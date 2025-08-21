# RDS PostgreSQL instance for tenant
# Each tenant gets their own isolated RDS instance

# Subnet group for RDS
resource "aws_db_subnet_group" "tenant" {
  name       = "${local.tenant_prefix}-db-subnet"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name   = "${local.tenant_prefix}-db-subnet"
    Tenant = var.tenant_name
  }
}

# Security group for RDS
resource "aws_security_group" "rds" {
  name        = "${local.tenant_prefix}-rds-sg"
  description = "Security group for ${var.tenant_name} RDS"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
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
    Name   = "${local.tenant_prefix}-rds-sg"
    Tenant = var.tenant_name
  }
}

# Generate secure password for RDS
resource "random_password" "db" {
  length  = 32
  special = true
}

# Store RDS credentials in Secrets Manager
resource "aws_secretsmanager_secret" "db" {
  name = "${local.tenant_prefix}-db-credentials"

  tags = {
    Name   = "${local.tenant_prefix}-db-credentials"
    Tenant = var.tenant_name
  }
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id

  secret_string = jsonencode({
    username          = "postgres"
    password          = random_password.db.result
    database          = replace(var.tenant_name, "-", "_")
    host              = aws_db_instance.tenant.address
    port              = 5432
    engine            = "postgres"
    connection_string = "postgresql://postgres:${random_password.db.result}@${aws_db_instance.tenant.endpoint}/${replace(var.tenant_name, "-", "_")}"
  })
}

# RDS PostgreSQL instance
resource "aws_db_instance" "tenant" {
  identifier = "${local.tenant_prefix}-db"

  # Engine
  engine               = "postgres"
  engine_version       = "15.7"
  instance_class       = local.config.rds_instance_class

  # Storage
  allocated_storage     = local.config.rds_allocated_storage
  max_allocated_storage = local.config.rds_max_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id           = var.kms_key_id

  # Database
  db_name  = replace(var.tenant_name, "-", "_")
  username = "postgres"
  password = random_password.db.result

  # Network
  db_subnet_group_name   = aws_db_subnet_group.tenant.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Backups
  backup_retention_period = local.config.rds_backup_retention
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  # High Availability
  multi_az = local.config.rds_multi_az

  # Performance Insights
  performance_insights_enabled = var.environment == "production"
  performance_insights_kms_key_id = var.environment == "production" ? var.kms_key_id : null
  performance_insights_retention_period = var.environment == "production" ? 7 : null

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql"]
  monitoring_interval             = var.environment == "production" ? 60 : 0
  monitoring_role_arn            = var.environment == "production" ? aws_iam_role.rds_monitoring[0].arn : null

  # Protection
  deletion_protection = var.enable_deletion_protection
  skip_final_snapshot = !var.enable_deletion_protection
  final_snapshot_identifier = var.enable_deletion_protection ? "${local.tenant_prefix}-db-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  tags = {
    Name   = "${local.tenant_prefix}-db"
    Tenant = var.tenant_name
  }
}

# IAM role for enhanced monitoring (production only)
resource "aws_iam_role" "rds_monitoring" {
  count = var.environment == "production" ? 1 : 0

  name = "${local.tenant_prefix}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count = var.environment == "production" ? 1 : 0

  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch alarms for RDS
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  count = try(local.config.enable_monitoring, false) ? 1 : 0

  alarm_name          = "${local.tenant_prefix}-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS CPU utilization"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.tenant.id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  count = try(local.config.enable_monitoring, false) ? 1 : 0

  alarm_name          = "${local.tenant_prefix}-rds-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "2147483648"  # 2GB in bytes
  alarm_description   = "This metric monitors RDS free storage"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.tenant.id
  }
}
