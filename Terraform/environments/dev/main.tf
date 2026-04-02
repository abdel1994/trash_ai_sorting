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