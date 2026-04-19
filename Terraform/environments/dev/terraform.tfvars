aws_region          = "eu-central-1"
aws_profile         = "trash_ai"
project_name        = "afval-ai"
vpc_cidr            = "10.0.0.0/16"
public_subnet_cidr  = "10.0.1.0/24"
private_subnet_cidr = "10.0.2.0/24"
availability_zone   = "eu-central-1a"

admin_ip_cidr     = "84.83.116.75/32"
tailscale_ip_cidr = "100.85.126.123/32"

bastion_instance_type     = "t3.micro"
bastion_key_name          = "ssh-key"
bastion_eip_allocation_id = "eipalloc-0617c83973d8e1e7d"
nat_instance_type         = "t3.micro"

mosquitto_instance_type = "t3.small"
mosquitto_key_name      = "ssh-key"
