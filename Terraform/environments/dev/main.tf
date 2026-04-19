module "network" {
  source = "../../modules/network"

  project_name        = var.project_name
  vpc_cidr            = var.vpc_cidr
  public_subnet_cidr  = var.public_subnet_cidr
  private_subnet_cidr = var.private_subnet_cidr
  availability_zone   = var.availability_zone
}

module "route_tables" {
  source = "../../modules/route_tables"

  project_name        = var.project_name
  vpc_id              = module.network.vpc_id
  public_subnet_id    = module.network.public_subnet_id
  private_subnet_id   = module.network.private_subnet_id
  internet_gateway_id = module.network.internet_gateway_id
}

locals {
  bastion_ingress_cidrs = compact([
    var.admin_ip_cidr,
    var.tailscale_ip_cidr
  ])
}

module "bastion_sg" {
  source = "../../modules/security_group"

  name                = "${var.project_name}-bastion-sg"
  description         = "Security group for bastion host"
  vpc_id              = module.network.vpc_id
  ingress_cidr_blocks = local.bastion_ingress_cidrs
  ingress_from_port   = 22
  ingress_to_port     = 22
  ingress_protocol    = "tcp"
}

module "nat_sg" {
  source = "../../modules/security_group"

  name                = "${var.project_name}-nat-sg"
  description         = "Security group for NAT instance"
  vpc_id              = module.network.vpc_id
  ingress_cidr_blocks = [var.private_subnet_cidr]
  ingress_from_port   = 0
  ingress_to_port     = 0
  ingress_protocol    = "-1"
}

module "private_sg" {
  source = "../../modules/security_group"

  name                             = "${var.project_name}-private-sg"
  description                      = "Security group for private instances"
  vpc_id                           = module.network.vpc_id
  create_ingress_from_sg           = true
  ingress_source_security_group_id = module.bastion_sg.security_group_id
  ingress_from_port                = 22
  ingress_to_port                  = 22
  ingress_protocol                 = "tcp"

}

// MQTT Ingress rules for Mosquitto broker in private instances
resource "aws_vpc_security_group_ingress_rule" "private_mqtt" {
  security_group_id = module.private_sg.security_group_id
  cidr_ipv4         = var.private_subnet_cidr
  from_port         = 1883
  to_port           = 1883
  ip_protocol       = "tcp"
  description       = "MQTT"
}

resource "aws_vpc_security_group_ingress_rule" "private_mqtt_tls" {
  security_group_id = module.private_sg.security_group_id
  cidr_ipv4         = var.private_subnet_cidr
  from_port         = 8883
  to_port           = 8883
  ip_protocol       = "tcp"
  description       = "MQTT TLS"
}

resource "aws_vpc_security_group_ingress_rule" "private_mqtt_from_bastion" {
  security_group_id            = module.private_sg.security_group_id
  referenced_security_group_id = module.bastion_sg.security_group_id
  from_port                    = 1883
  to_port                      = 1883
  ip_protocol                  = "tcp"
  description                  = "MQTT from bastion tunnel"
}


// dit is de ami lookup omdat ami id's regio gebonden zijn en kunnen veranderen // 
data "aws_ami" "ubuntu_bastion" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}


module "bastion" {
  source = "../../modules/ec2"

  name                        = "${var.project_name}-bastion"
  ami_id                      = data.aws_ami.ubuntu_bastion.id
  instance_type               = var.bastion_instance_type
  subnet_id                   = module.network.public_subnet_id
  security_group_ids          = [module.bastion_sg.security_group_id]
  key_name                    = var.bastion_key_name
  associate_public_ip_address = true
  root_volume_size            = 8
}

// toewijzing van elastic ip (persistent ) // 
resource "aws_eip_association" "bastion" {
  instance_id   = module.bastion.instance_id
  allocation_id = var.bastion_eip_allocation_id
}

resource "local_file" "ansible_inventory" {
  filename = "${path.module}/../../../Ansible/inventory/hosts.ini"

  content = <<-EOF
[bastion]
bastion-host ansible_host=${aws_eip_association.bastion.public_ip}

[mosquitto]
mosquitto-broker ansible_host=${module.mosquitto.private_ip} ansible_ssh_common_args='-o ProxyCommand="ssh -i ~/.ssh/ssh-key.pem -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -W %h:%p ubuntu@${aws_eip_association.bastion.public_ip}"'
EOF
}

resource "local_file" "ansible_inventory_tailscale" {
  filename = "${path.module}/../../../Ansible/inventory/hosts-tailscale.ini"

  content = <<-EOF
[bastion]
bastion-host ansible_host=bastion-trash-ai

[mosquitto]
mosquitto-broker ansible_host=${module.mosquitto.private_ip} ansible_ssh_common_args='-o ProxyCommand="ssh -i ~/.ssh/ssh-key.pem -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -W %h:%p ubuntu@bastion-trash-ai"'
EOF
}

// ami lookup  NAT ec2 Instance
data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

module "nat" {
  source = "../../modules/ec2"

  name                        = "${var.project_name}-nat"
  ami_id                      = data.aws_ssm_parameter.al2023_ami.value
  instance_type               = var.nat_instance_type
  subnet_id                   = module.network.public_subnet_id
  security_group_ids          = [module.nat_sg.security_group_id]
  key_name                    = var.bastion_key_name
  associate_public_ip_address = true
  root_volume_size            = 8
  source_dest_check           = false

  user_data = <<-EOF
              #!/bin/bash
              set -eux

              sysctl -w net.ipv4.ip_forward=1
              echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf

              dnf install -y iptables-services

              PRIMARY_IF=$(ip route show default | awk '/default/ {print $5}' | head -n1)

              iptables -t nat -A POSTROUTING -o $${PRIMARY_IF} -j MASQUERADE
              service iptables save

              systemctl enable iptables
              systemctl restart iptables
              EOF
}

// private subnet  route naar NAT //

resource "aws_route" "private_nat_outbound" {
  route_table_id         = module.route_tables.private_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  network_interface_id   = module.nat.primary_network_interface_id
}

// Mosquitto MQTT Broker in private subnet
module "mosquitto" {
  source = "../../modules/ec2"

  name               = "${var.project_name}-mosquitto"
  ami_id             = data.aws_ami.ubuntu_bastion.id
  instance_type      = var.mosquitto_instance_type
  subnet_id          = module.network.private_subnet_id
  security_group_ids = [module.private_sg.security_group_id]
  key_name           = var.mosquitto_key_name
  root_volume_size   = 20
}
