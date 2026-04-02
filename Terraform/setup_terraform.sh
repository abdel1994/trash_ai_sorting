#!/usr/bin/env bash
set -euo pipefail

echo "Terraform basisstructuur wordt aangemaakt..."

mkdir -p environments/dev
mkdir -p modules/network
mkdir -p modules/security_group
mkdir -p modules/ec2

cat > versions.tf <<'EOF'
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
EOF

cat > environments/dev/providers.tf <<'EOF'
provider "aws" {
  region = var.aws_region
}
EOF

cat > environments/dev/variables.tf <<'EOF'
variable "aws_region" {
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
EOF

cat > environments/dev/terraform.tfvars <<'EOF'
aws_region          = "eu-central-1"
project_name        = "afval-ai"
vpc_cidr            = "10.0.0.0/16"
public_subnet_cidr  = "10.0.1.0/24"
private_subnet_cidr = "10.0.2.0/24"
availability_zone   = "eu-central-1a"
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
EOF

cat > modules/network/variables.tf <<'EOF'
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
EOF

cat > modules/network/main.tf <<'EOF'
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet"
  }
}

resource "aws_subnet" "private" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.private_subnet_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = false

  tags = {
    Name = "${var.project_name}-private-subnet"
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}
EOF

cat > modules/network/outputs.tf <<'EOF'
output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_id" {
  value = aws_subnet.public.id
}

output "private_subnet_id" {
  value = aws_subnet.private.id
}

output "internet_gateway_id" {
  value = aws_internet_gateway.this.id
}
EOF

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
EOF

cat > modules/security_group/outputs.tf <<'EOF'
output "security_group_id" {
  value = aws_security_group.this.id
}
EOF

cat > modules/ec2/variables.tf <<'EOF'
variable "name" {
  type = string
}

variable "ami_id" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "security_group_ids" {
  type = list(string)
}
EOF

cat > modules/ec2/main.tf <<'EOF'
resource "aws_instance" "this" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = var.security_group_ids

  tags = {
    Name = var.name
  }
}
EOF

cat > modules/ec2/outputs.tf <<'EOF'
output "instance_id" {
  value = aws_instance.this.id
}

output "private_ip" {
  value = aws_instance.this.private_ip
}

output "public_ip" {
  value = aws_instance.this.public_ip
}
EOF

echo "Bestanden aangemaakt."
echo "Ga nu naar environments/dev en run:"
echo "terraform init"
echo "terraform fmt -recursive"
echo "terraform validate"
echo "terraform plan"
