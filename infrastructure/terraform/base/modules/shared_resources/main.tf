# Shared Resources Module - Resources used by all tenants

# Shared RDS Subnet Group
resource "aws_db_subnet_group" "shared" {
  name       = "mate-${var.environment}-shared"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "mate-${var.environment}-shared"
    Environment = var.environment
  }
}

# Shared ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "shared" {
  name       = "mate-${var.environment}-shared"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "mate-${var.environment}-shared"
    Environment = var.environment
  }
}

# Shared Security Group for internal services
resource "aws_security_group" "internal" {
  name        = "mate-${var.environment}-internal"
  description = "Security group for internal services"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "mate-${var.environment}-internal"
    Environment = var.environment
  }
}

# CloudWatch Log Group for ECS
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/mate-${var.environment}"
  retention_in_days = 30
  kms_key_id        = var.kms_key_id

  tags = {
    Name        = "mate-${var.environment}-ecs-logs"
    Environment = var.environment
  }
}

# Shared EFS for AI/ML Models (accessible by all tenants)
resource "aws_efs_file_system" "shared_models" {
  creation_token = "mate-${var.environment}-shared-models"
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
    Name        = "mate-${var.environment}-shared-models"
    Environment = var.environment
    Type        = "shared"
    Purpose     = "ai-models"
  }
}

# EFS Mount Targets for shared models
resource "aws_efs_mount_target" "shared_models" {
  count = length(var.private_subnet_ids)
  
  file_system_id  = aws_efs_file_system.shared_models.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [aws_security_group.efs.id]
}

# Security Group for shared EFS
resource "aws_security_group" "efs" {
  name        = "mate-${var.environment}-shared-efs-sg"
  description = "Security group for shared EFS mount targets"
  vpc_id      = var.vpc_id
  
  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.internal.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name        = "mate-${var.environment}-shared-efs-sg"
    Environment = var.environment
  }
}

# EFS Access Points for each tenant to access shared models
# These will be created dynamically by the tenant module