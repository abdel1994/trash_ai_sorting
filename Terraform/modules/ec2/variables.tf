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

variable "key_name" {
  type    = string
  default = null
}

variable "associate_public_ip_address" {
  type    = bool
  default = false
}

variable "root_volume_size" {
  type    = number
  default = 8
}

variable "source_dest_check" {
  type    = bool
  default = true
}

variable "user_data" {
  type    = string
  default = null
}