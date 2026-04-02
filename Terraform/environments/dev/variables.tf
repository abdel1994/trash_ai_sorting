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

variable "bastion_instance_type" {
  type = string
}

variable "bastion_key_name" {
  type = string
}

variable "bastion_eip_allocation_id" {
  type = string
}