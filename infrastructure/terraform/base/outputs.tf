# Outputs from base infrastructure needed by tenant deployments

output "vpc_id" {
  value = module.vpc.vpc_id
  description = "VPC ID for tenant resources"
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
  description = "Private subnet IDs for tenant resources"
}

output "public_subnet_ids" {
  value = module.vpc.public_subnet_ids
  description = "Public subnet IDs for tenant ALBs"
}

output "ecs_cluster_id" {
  value = module.ecs_cluster.cluster_id
  description = "ECS cluster ID for tenant services"
}

output "ecs_cluster_name" {
  value = module.ecs_cluster.cluster_name
  description = "ECS cluster name for tenant services"
}

output "ecr_repositories" {
  value = module.ecr.repository_urls
  description = "ECR repository URLs for container images"
}

output "ecr_registry" {
  value = module.ecr.ecr_registry
  description = "ECR registry URL"
}

output "cognito_user_pool_id" {
  value = module.cognito.user_pool_id
  description = "Cognito User Pool ID for authentication"
}

output "cognito_user_pool_domain" {
  value = module.cognito.user_pool_domain
  description = "Cognito User Pool domain"
}

output "cognito_app_client_id" {
  value = module.cognito.app_client_id
  description = "Cognito App Client ID"
}

output "cognito_app_client_secret" {
  value = module.cognito.app_client_secret
  description = "Cognito App Client Secret"
  sensitive = true
}

output "kms_key_id" {
  value = aws_kms_key.main.arn
  description = "KMS key ARN for encryption"
}

output "certificate_arn" {
  value = aws_acm_certificate.main.arn
  description = "ACM certificate ARN for HTTPS"
}

output "route53_zone_id" {
  value = local.zone_id
  description = "Route53 hosted zone ID"
}

output "waf_web_acl_id" {
  value = module.waf.web_acl_id
  description = "WAF Web ACL ID for protection"
}

output "shared_models_efs_id" {
  value = module.shared_resources.shared_models_efs_id
  description = "Shared EFS ID for base AI models"
}

output "domain_name" {
  value = var.domain_name
  description = "Base domain name"
}

output "aws_region" {
  value = var.aws_region
  description = "AWS region"
}
