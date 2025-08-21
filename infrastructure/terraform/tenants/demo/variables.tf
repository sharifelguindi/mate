variable "tenant_name" {
  description = "Name of the tenant"
  type        = string
  default     = "demo"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "tenant_config" {
  description = "Tenant configuration"
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