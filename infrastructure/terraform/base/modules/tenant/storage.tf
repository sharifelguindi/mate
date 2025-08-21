# Storage resources for tenant (S3 and EFS)

# S3 Bucket for tenant data
resource "aws_s3_bucket" "tenant_data" {
  bucket = "${local.tenant_prefix}-data"
  
  tags = {
    Name   = "${local.tenant_prefix}-data"
    Tenant = var.tenant_name
    HIPAA  = local.config.hipaa_compliant ? "true" : "false"
  }
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "tenant_data" {
  bucket = aws_s3_bucket.tenant_data.id
  
  versioning_configuration {
    status = local.config.s3_versioning ? "Enabled" : "Disabled"
  }
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "tenant_data" {
  bucket = aws_s3_bucket.tenant_data.id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_id
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "tenant_data" {
  bucket = aws_s3_bucket.tenant_data.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Lifecycle Rules
resource "aws_s3_bucket_lifecycle_configuration" "tenant_data" {
  count = local.config.s3_lifecycle_rules ? 1 : 0
  
  bucket = aws_s3_bucket.tenant_data.id
  
  rule {
    id     = "archive-old-data"
    status = "Enabled"
    
    filter {}
    
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 180
      storage_class = "GLACIER"
    }
    
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
    
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    
    noncurrent_version_transition {
      noncurrent_days = 60
      storage_class   = "GLACIER"
    }
    
    noncurrent_version_expiration {
      noncurrent_days = local.config.data_retention_days
    }
  }
  
  rule {
    id     = "delete-incomplete-uploads"
    status = "Enabled"
    
    filter {}
    
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# S3 Bucket Logging
resource "aws_s3_bucket_logging" "tenant_data" {
  count = local.config.enable_audit_logging ? 1 : 0
  
  bucket = aws_s3_bucket.tenant_data.id
  
  target_bucket = aws_s3_bucket.audit_logs[0].id
  target_prefix = "s3-access-logs/"
}

# S3 Bucket for Audit Logs (HIPAA requirement)
resource "aws_s3_bucket" "audit_logs" {
  count = local.config.enable_audit_logging ? 1 : 0
  
  bucket = "${local.tenant_prefix}-audit-logs"
  
  tags = {
    Name   = "${local.tenant_prefix}-audit-logs"
    Tenant = var.tenant_name
    HIPAA  = "true"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_logs" {
  count = local.config.enable_audit_logging ? 1 : 0
  
  bucket = aws_s3_bucket.audit_logs[0].id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_id
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "audit_logs" {
  count = local.config.enable_audit_logging ? 1 : 0
  
  bucket = aws_s3_bucket.audit_logs[0].id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "audit_logs" {
  count = local.config.enable_audit_logging ? 1 : 0
  
  bucket = aws_s3_bucket.audit_logs[0].id
  
  rule {
    id     = "retain-audit-logs"
    status = "Enabled"
    
    filter {}
    
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
    
    expiration {
      days = local.config.data_retention_days
    }
  }
}

# EFS File System for shared models
resource "aws_efs_file_system" "models" {
  creation_token = "${local.tenant_prefix}-models"
  encrypted      = true
  kms_key_id     = var.kms_key_id
  
  throughput_mode                 = "bursting"
  provisioned_throughput_in_mibps = null
  
  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }
  
  lifecycle_policy {
    transition_to_primary_storage_class = "AFTER_1_ACCESS"
  }
  
  tags = {
    Name   = "${local.tenant_prefix}-models"
    Tenant = var.tenant_name
  }
}

# EFS File System for tenant-specific data
resource "aws_efs_file_system" "tenant_data" {
  creation_token = "${local.tenant_prefix}-data"
  encrypted      = true
  kms_key_id     = var.kms_key_id
  
  throughput_mode = local.config.efs_throughput_mode
  provisioned_throughput_in_mibps = local.config.efs_throughput_mode == "provisioned" ? local.config.efs_throughput_mibps : null
  
  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }
  
  lifecycle_policy {
    transition_to_primary_storage_class = "AFTER_1_ACCESS"
  }
  
  tags = {
    Name   = "${local.tenant_prefix}-tenant-data"
    Tenant = var.tenant_name
  }
}

# EFS Mount Targets for models
resource "aws_efs_mount_target" "models" {
  for_each = toset(var.private_subnet_ids)
  
  file_system_id  = aws_efs_file_system.models.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

# EFS Mount Targets for tenant data
resource "aws_efs_mount_target" "tenant_data" {
  for_each = toset(var.private_subnet_ids)
  
  file_system_id  = aws_efs_file_system.tenant_data.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

# Security Group for EFS
resource "aws_security_group" "efs" {
  name        = "${local.tenant_prefix}-efs-sg"
  description = "Security group for ${var.tenant_name} EFS"
  vpc_id      = var.vpc_id
  
  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.tenant.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name   = "${local.tenant_prefix}-efs-sg"
    Tenant = var.tenant_name
  }
}

# EFS Access Points for better isolation
# Access point for tenant's custom models
resource "aws_efs_access_point" "tenant_models" {
  file_system_id = aws_efs_file_system.models.id
  
  posix_user {
    gid = 1000
    uid = 1000
  }
  
  root_directory {
    path = "/models"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }
  
  tags = {
    Name   = "${local.tenant_prefix}-models-ap"
    Tenant = var.tenant_name
  }
}

# Access point for shared base models (read-only access)
resource "aws_efs_access_point" "shared_models" {
  file_system_id = var.shared_models_efs_id
  
  posix_user {
    gid = 1000
    uid = 1000
  }
  
  root_directory {
    path = "/base-models/${var.tenant_name}"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }
  
  tags = {
    Name   = "${local.tenant_prefix}-shared-models-ap"
    Tenant = var.tenant_name
    Type   = "shared-readonly"
  }
}

resource "aws_efs_access_point" "tenant_data" {
  file_system_id = aws_efs_file_system.tenant_data.id
  
  posix_user {
    gid = 1000
    uid = 1000
  }
  
  root_directory {
    path = "/${var.tenant_name}"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }
  
  tags = {
    Name   = "${local.tenant_prefix}-data-ap"
    Tenant = var.tenant_name
  }
}

# CloudWatch Alarms for Storage
resource "aws_cloudwatch_metric_alarm" "s3_bucket_size" {
  count = var.environment == "production" ? 1 : 0
  
  alarm_name          = "${local.tenant_prefix}-s3-size"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "BucketSizeBytes"
  namespace          = "AWS/S3"
  period             = "86400"
  statistic          = "Average"
  threshold          = local.config.max_storage_gb * 1073741824  # Convert GB to bytes
  alarm_description  = "Alert when S3 bucket size exceeds limit"
  # alarm_actions      = [aws_sns_topic.alerts[0].arn]  # TODO: Add SNS topic for alerts
  
  dimensions = {
    BucketName = aws_s3_bucket.tenant_data.bucket
    StorageType = "StandardStorage"
  }
  
  tags = {
    Name   = "${local.tenant_prefix}-s3-size-alarm"
    Tenant = var.tenant_name
  }
}