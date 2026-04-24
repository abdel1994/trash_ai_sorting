# Netwerk
module "network" {
  source = "../../modules/network"

  project_name        = var.project_name
  vpc_cidr            = var.vpc_cidr
  public_subnet_cidr  = var.public_subnet_cidr
  private_subnet_cidr = var.private_subnet_cidr
  availability_zone   = var.availability_zone
}

# Routing
module "route_tables" {
  source = "../../modules/route_tables"

  project_name        = var.project_name
  vpc_id              = module.network.vpc_id
  public_subnet_id    = module.network.public_subnet_id
  private_subnet_id   = module.network.private_subnet_id
  internet_gateway_id = module.network.internet_gateway_id
}

# Tweede private subnet voor database
resource "aws_subnet" "private_rds" {
  vpc_id                  = module.network.vpc_id
  cidr_block              = var.private_subnet_cidr_secondary
  availability_zone       = var.availability_zone_secondary
  map_public_ip_on_launch = false

  tags = {
    Name = "${var.project_name}-private-db-subnet"
  }
}

resource "aws_route_table_association" "private_rds" {
  subnet_id      = aws_subnet.private_rds.id
  route_table_id = module.route_tables.private_route_table_id
}

# Toegangslijst bastion
locals {
  bastion_ingress_cidrs = compact([
    var.admin_ip_cidr,
    var.tailscale_ip_cidr
  ])
}

# Security groups
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

# API en dashboard security groups
module "api_sg" {
  source = "../../modules/security_group"

  name                             = "${var.project_name}-api-sg"
  description                      = "Security group for API instance"
  vpc_id                           = module.network.vpc_id
  create_ingress_from_sg           = true
  ingress_source_security_group_id = module.bastion_sg.security_group_id
  ingress_from_port                = 22
  ingress_to_port                  = 22
  ingress_protocol                 = "tcp"
}

module "dashboard_sg" {
  source = "../../modules/security_group"

  name                             = "${var.project_name}-dashboard-sg"
  description                      = "Security group for dashboard instance"
  vpc_id                           = module.network.vpc_id
  create_ingress_from_sg           = true
  ingress_source_security_group_id = module.bastion_sg.security_group_id
  ingress_from_port                = 22
  ingress_to_port                  = 22
  ingress_protocol                 = "tcp"
}

module "db_sg" {
  source = "../../modules/security_group"

  name                             = "${var.project_name}-db-sg"
  description                      = "Security group for PostgreSQL database"
  vpc_id                           = module.network.vpc_id
  create_ingress_from_sg           = true
  ingress_source_security_group_id = module.api_sg.security_group_id
  ingress_from_port                = 5432
  ingress_to_port                  = 5432
  ingress_protocol                 = "tcp"
}

# App toegang
resource "aws_vpc_security_group_ingress_rule" "api_from_dashboard" {
  security_group_id            = module.api_sg.security_group_id
  referenced_security_group_id = module.dashboard_sg.security_group_id
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
  description                  = "Dashboard to API"
}

resource "aws_vpc_security_group_ingress_rule" "api_from_bastion" {
  security_group_id            = module.api_sg.security_group_id
  referenced_security_group_id = module.bastion_sg.security_group_id
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
  description                  = "Bastion to API"
}

resource "aws_vpc_security_group_ingress_rule" "dashboard_from_bastion" {
  security_group_id            = module.dashboard_sg.security_group_id
  referenced_security_group_id = module.bastion_sg.security_group_id
  from_port                    = 3000
  to_port                      = 3000
  ip_protocol                  = "tcp"
  description                  = "Bastion to dashboard"
}

resource "aws_vpc_security_group_ingress_rule" "db_from_bastion" {
  security_group_id            = module.db_sg.security_group_id
  referenced_security_group_id = module.bastion_sg.security_group_id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "Bastion to PostgreSQL"
}

resource "aws_vpc_security_group_ingress_rule" "db_ssh_from_bastion" {
  security_group_id            = module.db_sg.security_group_id
  referenced_security_group_id = module.bastion_sg.security_group_id
  from_port                    = 22
  to_port                      = 22
  ip_protocol                  = "tcp"
  description                  = "Bastion to database SSH"
}

# MQTT toegang
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

# AMI lookup
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

# Bastion host
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

# Koppel vaste EIP
resource "aws_eip_association" "bastion" {
  instance_id   = module.bastion.instance_id
  allocation_id = var.bastion_eip_allocation_id
}

# NAT AMI
data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# Bootstrap scripts
locals {
  docker_user_data = <<-EOF
                     #!/bin/bash
                     set -eux

                     apt-get update -y
                     apt-get install -y ca-certificates curl
                     install -m 0755 -d /etc/apt/keyrings
                     curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
                     chmod a+r /etc/apt/keyrings/docker.asc
                     echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" > /etc/apt/sources.list.d/docker.list
                     apt-get update -y
                     apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
                     systemctl enable docker
                     systemctl start docker
                     usermod -aG docker ubuntu
                     EOF

  postgres_user_data = <<-EOF
                       #!/bin/bash
                       set -eux

                       export DEBIAN_FRONTEND=noninteractive
                       apt-get update -y
                       apt-get install -y postgresql postgresql-contrib

                       PG_VERSION=$(ls /etc/postgresql | sort -V | tail -n1)
                       PG_CONF="/etc/postgresql/$${PG_VERSION}/main/postgresql.conf"
                       PG_HBA="/etc/postgresql/$${PG_VERSION}/main/pg_hba.conf"

                       sed -i "s/^#listen_addresses =.*/listen_addresses = '*'/" "$${PG_CONF}"
                       echo "host    all             all             ${var.vpc_cidr}            scram-sha-256" >> "$${PG_HBA}"

                       systemctl enable postgresql
                       systemctl restart postgresql
                       EOF
}

# NAT instance
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

# Default route via NAT
resource "aws_route" "private_nat_outbound" {
  route_table_id         = module.route_tables.private_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  network_interface_id   = module.nat.primary_network_interface_id
}

# Mosquitto broker
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

# API server
module "api" {
  source = "../../modules/ec2"

  name               = "${var.project_name}-api"
  ami_id             = data.aws_ami.ubuntu_bastion.id
  instance_type      = var.api_instance_type
  subnet_id          = module.network.private_subnet_id
  security_group_ids = [module.api_sg.security_group_id]
  key_name           = var.bastion_key_name
  root_volume_size   = 20
  user_data          = local.docker_user_data
}

# Dashboard server
module "dashboard" {
  source = "../../modules/ec2"

  name               = "${var.project_name}-dashboard"
  ami_id             = data.aws_ami.ubuntu_bastion.id
  instance_type      = var.dashboard_instance_type
  subnet_id          = module.network.private_subnet_id
  security_group_ids = [module.dashboard_sg.security_group_id]
  key_name           = var.bastion_key_name
  root_volume_size   = 20
  user_data          = local.docker_user_data
}

# Database servers
resource "aws_vpc_security_group_ingress_rule" "db_from_db" {
  security_group_id            = module.db_sg.security_group_id
  referenced_security_group_id = module.db_sg.security_group_id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "Database sync verkeer"
}

module "db_primary" {
  source = "../../modules/ec2"

  name               = "${var.project_name}-postgres-primary"
  ami_id             = data.aws_ami.ubuntu_bastion.id
  instance_type      = var.db_instance_type
  subnet_id          = module.network.private_subnet_id
  security_group_ids = [module.db_sg.security_group_id]
  key_name           = var.db_key_name
  root_volume_size   = 30
  user_data          = local.postgres_user_data
}

module "db_secondary" {
  source = "../../modules/ec2"

  name               = "${var.project_name}-postgres-secondary"
  ami_id             = data.aws_ami.ubuntu_bastion.id
  instance_type      = var.db_instance_type
  subnet_id          = aws_subnet.private_rds.id
  security_group_ids = [module.db_sg.security_group_id]
  key_name           = var.db_key_name
  root_volume_size   = 30
  user_data          = local.postgres_user_data
}
