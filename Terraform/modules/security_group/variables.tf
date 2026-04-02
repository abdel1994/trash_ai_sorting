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

variable "create_ingress_from_sg" {
  type    = bool
  default = false
}

