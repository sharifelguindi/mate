output "db_subnet_group_name" {
  value = aws_db_subnet_group.shared.name
}

output "elasticache_subnet_group_name" {
  value = aws_elasticache_subnet_group.shared.name
}

output "internal_security_group_id" {
  value = aws_security_group.internal.id
}

output "ecs_log_group_name" {
  value = aws_cloudwatch_log_group.ecs.name
}

output "shared_models_efs_id" {
  value = aws_efs_file_system.shared_models.id
  description = "ID of the shared EFS file system for AI models"
}

output "shared_models_efs_arn" {
  value = aws_efs_file_system.shared_models.arn
  description = "ARN of the shared EFS file system for AI models"
}

output "efs_security_group_id" {
  value = aws_security_group.efs.id
  description = "Security group ID for EFS access"
}
