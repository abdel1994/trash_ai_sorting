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

output "bastion_instance_id" {
  value = module.bastion.instance_id
}

output "bastion_private_ip" {
  value = module.bastion.private_ip
}

output "bastion_eip_allocation_id" {
  value = aws_eip_association.bastion.allocation_id
}

output "bastion_public_ip" {
  value = module.bastion.public_ip
}

output "nat_instance_id" {
  value = module.nat.instance_id
}

output "nat_private_ip" {
  value = module.nat.private_ip
}

output "nat_public_ip" {
  value = module.nat.public_ip
}