output "bastion_eip_allocation_id" {
  value = aws_eip.bastion.id
}

output "bastion_eip_public_ip" {
  value = aws_eip.bastion.public_ip
}