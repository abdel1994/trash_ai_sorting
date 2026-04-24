# Outputs persistent

output "bastion_eip_allocation_id" { value = aws_eip.bastion.id }

output "bastion_eip_public_ip" { value = aws_eip.bastion.public_ip }

# outputs voor test omgeving # 

output "bastion_test_eip_allocation_id" { value = aws_eip.bastion_test.id }

output "bastion_test_public_ip" { value = aws_eip.bastion_test.public_ip }

output "db_primary_volume_id" { value = aws_ebs_volume.db_primary_data.id }

output "best_pt_bucket_name" { value = aws_s3_bucket.best_pt.bucket }
