# ElastiCache Redis for tenant
# Each tenant gets their own isolated Redis instance

# Subnet group for ElastiCache
resource "aws_elasticache_subnet_group" "tenant" {
  name       = "${local.tenant_prefix}-redis-subnet"
  subnet_ids = var.private_subnet_ids
  
  tags = {
    Name   = "${local.tenant_prefix}-redis-subnet"
    Tenant = var.tenant_name
  }
}

# Security group for Redis
resource "aws_security_group" "redis" {
  name        = "${local.tenant_prefix}-redis-sg"
  description = "Security group for ${var.tenant_name} Redis"
  vpc_id      = var.vpc_id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
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
    Name   = "${local.tenant_prefix}-redis-sg"
    Tenant = var.tenant_name
  }
}

# Generate auth token for Redis
resource "random_password" "redis_auth" {
  length  = 32
  special = false  # Redis auth tokens don't like special chars
}

# Store Redis credentials in Secrets Manager
resource "aws_secretsmanager_secret" "redis" {
  name = "${local.tenant_prefix}-redis-credentials"
  
  tags = {
    Name   = "${local.tenant_prefix}-redis-credentials"
    Tenant = var.tenant_name
  }
}

resource "aws_secretsmanager_secret_version" "redis" {
  secret_id = aws_secretsmanager_secret.redis.id
  
  secret_string = jsonencode({
    endpoint   = aws_elasticache_replication_group.tenant.primary_endpoint_address
    port       = 6379
    auth_token = random_password.redis_auth.result
  })
}

# ElastiCache Replication Group (Redis Cluster)
resource "aws_elasticache_replication_group" "tenant" {
  replication_group_id = "${local.tenant_prefix}-redis"
  description          = "Redis cluster for ${var.tenant_name}"
  
  # Engine
  engine               = "redis"
  engine_version      = "7.0"
  port                = 6379
  
  # Nodes
  node_type                  = local.config.redis_node_type
  num_cache_clusters         = local.config.redis_num_cache_nodes
  automatic_failover_enabled = local.config.redis_num_cache_nodes > 1
  multi_az_enabled          = local.config.redis_num_cache_nodes > 1
  
  # Network
  subnet_group_name = aws_elasticache_subnet_group.tenant.name
  security_group_ids = [aws_security_group.redis.id]
  
  # Security
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                = random_password.redis_auth.result
  kms_key_id               = var.kms_key_id
  
  # Parameter group
  parameter_group_name = aws_elasticache_parameter_group.tenant.name
  
  # Backups
  snapshot_retention_limit = local.config.redis_backup_retention
  snapshot_window         = "03:00-05:00"
  
  # Maintenance
  maintenance_window = "sun:05:00-sun:07:00"
  
  # Notifications
  # notification_topic_arn = local.config.enable_monitoring ? aws_sns_topic.tenant_alerts[0].arn : null
  
  # Logs
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }
  
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_engine.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }
  
  tags = {
    Name   = "${local.tenant_prefix}-redis"
    Tenant = var.tenant_name
  }
}

# Parameter group for Redis
resource "aws_elasticache_parameter_group" "tenant" {
  family = "redis7"
  name   = "${local.tenant_prefix}-redis-params"
  
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
  
  parameter {
    name  = "timeout"
    value = "300"
  }
  
  tags = {
    Name   = "${local.tenant_prefix}-redis-params"
    Tenant = var.tenant_name
  }
}

# CloudWatch Log Groups for Redis
resource "aws_cloudwatch_log_group" "redis_slow" {
  name              = "/aws/elasticache/${local.tenant_prefix}-redis/slow-log"
  retention_in_days = 7
  kms_key_id        = var.kms_key_id
  
  tags = {
    Name   = "${local.tenant_prefix}-redis-slow-logs"
    Tenant = var.tenant_name
  }
}

resource "aws_cloudwatch_log_group" "redis_engine" {
  name              = "/aws/elasticache/${local.tenant_prefix}-redis/engine-log"
  retention_in_days = 7
  kms_key_id        = var.kms_key_id
  
  tags = {
    Name   = "${local.tenant_prefix}-redis-engine-logs"
    Tenant = var.tenant_name
  }
}

# CloudWatch alarms for Redis
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  count = try(local.config.enable_monitoring, false) ? 1 : 0
  
  alarm_name          = "${local.tenant_prefix}-redis-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors Redis CPU utilization"
  
  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.tenant.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  count = try(local.config.enable_monitoring, false) ? 1 : 0
  
  alarm_name          = "${local.tenant_prefix}-redis-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors Redis memory usage"
  
  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.tenant.id
  }
}