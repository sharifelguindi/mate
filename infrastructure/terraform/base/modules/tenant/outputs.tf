output "web_url" {
  description = "Web URL for the tenant"
  value       = "https://${var.tenant_config.subdomain}.${var.domain_name}"
}

output "alb_dns" {
  description = "ALB DNS name"
  value       = aws_lb.tenant.dns_name
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.tenant.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = aws_elasticache_replication_group.tenant.primary_endpoint_address
  sensitive   = true
}

output "s3_bucket" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.tenant_data.bucket
}

output "django_task_definition_arn" {
  description = "Django task definition ARN"
  value       = aws_ecs_task_definition.django.arn
}

output "celery_task_definition_arn" {
  description = "Celery task definition ARN"
  value       = aws_ecs_task_definition.celery.arn
}

output "beat_task_definition_arn" {
  description = "Beat task definition ARN"
  value       = aws_ecs_task_definition.beat.arn
}

output "django_service_name" {
  description = "Django ECS service name"
  value       = aws_ecs_service.django.name
}

output "celery_service_name" {
  description = "Celery ECS service name"
  value       = aws_ecs_service.celery.name
}

output "beat_service_name" {
  description = "Beat ECS service name"
  value       = aws_ecs_service.beat.name
}

output "efs_models_id" {
  description = "EFS file system ID for models"
  value       = aws_efs_file_system.models.id
}

output "efs_tenant_data_id" {
  description = "EFS file system ID for tenant data"
  value       = aws_efs_file_system.tenant_data.id
}

output "django_secret_arn" {
  description = "Django secrets ARN"
  value       = aws_secretsmanager_secret.django.arn
  sensitive   = true
}

output "rds_secret_arn" {
  description = "RDS secret ARN"
  value       = aws_secretsmanager_secret.db.arn
  sensitive   = true
}

output "redis_secret_arn" {
  description = "Redis secret ARN"
  value       = aws_secretsmanager_secret.redis.arn
  sensitive   = true
}