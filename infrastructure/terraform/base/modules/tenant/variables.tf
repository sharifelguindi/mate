variable "tenant_name" {
  description = "Name of the tenant (used for resource naming)"
  type        = string
}

variable "tenant_config" {
  description = "Configuration for the tenant"
  type = object({
    display_name              = string
    subdomain                = string
    tier                     = string
    
    # RDS Configuration
    rds_instance_class       = optional(string)
    rds_allocated_storage    = optional(number, 20)
    rds_max_storage         = optional(number, 100)
    rds_backup_retention    = optional(number, 7)
    rds_multi_az           = optional(bool, false)
    
    # ElastiCache Configuration
    redis_node_type        = optional(string)
    redis_num_cache_nodes  = optional(number, 1)
    redis_backup_retention = optional(number, 0)
    
    # ECS Service Configuration
    django_desired_count   = optional(number, 1)
    django_cpu            = optional(number)
    django_memory         = optional(number)
    celery_desired_count  = optional(number, 1)
    celery_cpu           = optional(number)
    celery_memory        = optional(number)
    
    # Auto-scaling
    enable_autoscaling     = optional(bool, false)
    min_capacity          = optional(number, 1)
    max_capacity          = optional(number, 3)
    target_cpu_utilization = optional(number, 75)
    
    # Storage
    s3_versioning         = optional(bool, true)
    s3_lifecycle_rules    = optional(bool, false)
    efs_throughput_mode   = optional(string, "bursting")
    efs_throughput_mibps  = optional(number)
    max_storage_gb        = optional(number, 100)
    
    # HIPAA Compliance
    hipaa_compliant       = optional(bool, false)
    enable_audit_logging  = optional(bool, false)
    enable_flow_logs      = optional(bool, false)
    data_retention_days   = optional(number, 90)
    
    # Identity Provider
    identity_provider = optional(object({
      type         = string
      name         = string
      metadata_url = optional(string)
      metadata_xml = optional(string)
    }))
    
    # Contact Information
    technical_contact = string
    billing_contact   = string
    
    # Cost allocation tags
    cost_center = optional(string)
    department  = optional(string)
  })
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where resources will be created"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "ecs_cluster_id" {
  description = "ECS cluster ID"
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS cluster name"
  type        = string
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
}

variable "ecr_repositories" {
  description = "Map of ECR repository URLs"
  type        = map(string)
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  type        = string
}

variable "cognito_user_pool_domain" {
  description = "Cognito User Pool domain"
  type        = string
}

variable "cognito_app_client_id" {
  description = "Cognito App Client ID"
  type        = string
}

variable "cognito_app_client_secret" {
  description = "Cognito App Client Secret"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Base domain name"
  type        = string
}

variable "certificate_arn" {
  description = "ACM certificate ARN"
  type        = string
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID"
  type        = string
}

variable "waf_web_acl_id" {
  description = "WAF Web ACL ID"
  type        = string
  default     = ""
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for RDS and other resources"
  type        = bool
  default     = false
}

variable "shared_models_efs_id" {
  description = "ID of the shared EFS file system for base AI models"
  type        = string
}

