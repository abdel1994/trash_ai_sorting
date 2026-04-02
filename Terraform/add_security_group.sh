#!/usr/bin/env bash
set -euo pipefail

echo "Security group module en dev-config worden bijgewerkt..."

mkdir -p modules/security_group

cat > modules/security_group/variables.tf <<'EOF'
variable "name" {
  type = string
}

variable "description" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "ingress_cidr_blocks" {
  type    = list(string)
  default = []
}

variable "ingress_source_security_group_id" {
  type    = string
  default = null
}

variable "ingress_from_port" {
  type = number
}

variable "ingress_to_port" {
  type = number
}

variable "ingress_protocol" {
  type = string
}
EOF

cat > modules/security_group/main.tf <<'EOF'
resource "aws_security_group" "this" {
  name        = var.name
  description = var.description
  vpc_id      = var.vpc_id

  tags = {
    Name = var.name
  }
}

resource "aws_vpc_security_group_ingress_rule" "cidr" {
  for_each = toset(var.ingress_cidr_blocks)

  security_group_id = aws_security_group.this.id
  cidr_ipv4         = each.value
  from_port         = var.ingress_from_port
  to_port           = var.ingress_to_port
  ip_protocol       = var.ingress_protocol
}

resource "aws_vpc_security_group_ingress_rule" "sg" {
  count = var.ingress_source_security_group_id != null ? 1 : 0

  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = var.ingress_source_security_group_id
  from_port                    = var.ingress_from_port
  to_port                      = var.ingress_to_port
  ip_protocol                  = var.ingress_protocol
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.this.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
EOF

cat > modules/security_group/outputs.tf <<'EOF'
output "security_group_id" {
  value = aws_security_group.this.id
}
EOF

cat > environments/dev/variables.tf <<'EOF'
variable "aws_region" {
  type = string
}

variable "aws_profile" {
  type = string
}

variable "project_name" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "public_subnet_cidr" {
  type = string
}

variable "private_subnet_cidr" {
  type = string
}

variable "availability_zone" {
  type = string
}

variable "admin_ip_cidr" {
  type = string
}

variable "tailscale_ip_cidr" {
  type    = string
  default = ""
}
EOF

cat > environments/dev/terraform.tfvars <<'EOF'
aws_region          = "eu-central-1"
aws_profile         = "trash_ai"
project_name        = "afval-ai"
vpc_cidr            = "10.0.0.0/16"
public_subnet_cidr  = "10.0.1.0/24"
private_subnet_cidr = "10.0.2.0/24"
availability_zone   = "eu-central-1a"

admin_ip_cidr       = "REPLACE_WITH_YOUR_PUBLIC_IP/32"
tailscale_ip_cidr   = ""
EOF

cat > environments/dev/providers.tf <<'EOF'
provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}
EOF

cat > environments/dev/main.tf <<'EOF'
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

  name           = "${var.project_name}-bastion-sg"
  description    = "Security group for bastion host"
  vpc_id         = module.network.vpc_id
  ingress_cidr_blocks = local.bastion_ingress_cidrs
  ingress_from_port   = 22
  ingress_to_port     = 22
  ingress_protocol    = "tcp"
}

module "nat_sg" {
  source = "../../modules/security_group"

  name           = "${var.project_name}-nat-sg"
  description    = "Security group for NAT instance"
  vpc_id         = module.network.vpc_id
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
  ingress_source_security_group_id = module.bastion_sg.security_group_id
  ingress_from_port                = 22
  ingress_to_port                  = 22
  ingress_protocol                 = "tcp"
}
EOF

cat > environments/dev/outputs.tf <<'EOF'
output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_id" {
  value = module.network.public_subnet_id
}

output "private_subnet_id" {
  value = module.network.private_subnet_id
}

output "internet_gateway_id" {
  value = module.network.internet_gateway_id
}

output "public_route_table_id" {
  value = module.route_tables.public_route_table_id
}

output "private_route_table_id" {
  value = module.route_tables.private_route_table_id
}

output "bastion_sg_id" {
  value = module.bastion_sg.security_group_id
}

output "nat_sg_id" {
  value = module.nat_sg.security_group_id
}

output "private_sg_id" {
  value = module.private_sg.security_group_id
}
EOF

echo "Klaar."
echo "Pas nu environments/dev/terraform.tfvars aan:"
echo '  admin_ip_cidr = "JOUW_IP/32"'
echo "Daarna run:"
echo "  cd environments/dev"
echo "  terraform fmt -recursive"
echo "  terraform validate"
echo "  terraform plan"
