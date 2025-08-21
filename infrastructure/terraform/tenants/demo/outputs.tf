output "tenant_url" {
  value       = module.tenant.web_url
  description = "URL for accessing the tenant application"
}

output "alb_dns" {
  value       = module.tenant.alb_dns
  description = "ALB DNS name"
}

output "rds_endpoint" {
  value       = module.tenant.rds_endpoint
  description = "RDS database endpoint"
  sensitive   = true
}

output "redis_endpoint" {
  value       = module.tenant.redis_endpoint
  description = "Redis cache endpoint"
  sensitive   = true
}

output "s3_bucket" {
  value       = module.tenant.s3_bucket
  description = "S3 bucket name for tenant data"
}

output "task_definitions" {
  value = {
    django = module.tenant.django_task_definition_arn
    celery = module.tenant.celery_task_definition_arn
    beat   = module.tenant.beat_task_definition_arn
  }
  description = "ECS task definition ARNs"
}