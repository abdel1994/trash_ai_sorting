# Vaste resources
resource "aws_eip" "bastion" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-bastion-eip"
  }
}

# elastic ip voor test omgeving # 

resource "aws_eip" "bastion_test" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-bastion-test_omgeving-eip"
  }
}

# Testomgeving state
data "terraform_remote_state" "test_omgeving" {
  backend = "local"

  config = {
    path = var.test_environment_state_path
  }
}

# Primary database volume
data "aws_instance" "db_primary" {
  instance_id = data.terraform_remote_state.test_omgeving.outputs.db_primary_instance_id
}

resource "aws_ebs_volume" "db_primary_data" {
  availability_zone = data.aws_instance.db_primary.availability_zone
  size              = var.db_primary_volume_size
  type              = "gp3"
  encrypted         = true

  tags = {
    Name = "${var.project_name}-db-primary-data"
  }
}

resource "aws_volume_attachment" "db_primary_data" {
  device_name = var.db_primary_device_name
  volume_id   = aws_ebs_volume.db_primary_data.id
  instance_id = data.aws_instance.db_primary.id
}

# Modelopslag
data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "best_pt" {
  bucket = "${var.project_name}-bestpt-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.project_name}-bestpt"
  }
}

resource "aws_s3_bucket_versioning" "best_pt" {
  bucket = aws_s3_bucket.best_pt.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "best_pt" {
  bucket = aws_s3_bucket.best_pt.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "best_pt" {
  bucket = aws_s3_bucket.best_pt.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "best_pt" {
  bucket = aws_s3_bucket.best_pt.id

  rule {
    id     = "expire-model-versions"
    status = "Enabled"

    filter {}

    expiration {
      days = 60
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
