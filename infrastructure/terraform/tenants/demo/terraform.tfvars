# Demo tenant configuration
tenant_name = "demo"
environment = "dev"

tenant_config = {
  # Basic identification
  display_name = "Demo Hospital"
  subdomain    = "demo"
  tier         = "trial"

  # Minimal RDS PostgreSQL
  rds_instance_class    = "db.t4g.micro"
  rds_allocated_storage = 20
  rds_max_storage      = 40
  rds_backup_retention = 3
  rds_multi_az        = false

  # Minimal Redis
  redis_node_type       = "cache.t4g.micro"
  redis_num_cache_nodes = 1
  redis_backup_retention = 0

  # ECS containers with adequate resources
  django_desired_count = 1
  django_cpu          = 1024
  django_memory       = 2048

  celery_desired_count = 1
  celery_cpu          = 512
  celery_memory       = 1024

  beat_cpu    = 256
  beat_memory = 512

  # No auto-scaling for demo
  enable_autoscaling = false
  enable_monitoring  = false

  # Storage settings with HIPAA compliance
  s3_versioning       = true
  s3_lifecycle_rules  = false
  efs_throughput_mode = "bursting"
  max_storage_gb      = 10

  # HIPAA compliance enabled
  hipaa_compliant      = true
  enable_audit_logging = true
  enable_flow_logs     = false
  data_retention_days  = 90

  # No SSO
  identity_provider = null

  # Contact info
  technical_contact = "admin@sociant.ai"
  billing_contact   = "admin@sociant.ai"

  # Admin user configuration
  admin_email    = "admin@demo.mate.sociant.ai"
  admin_username = "admin"

  # Cost tracking
  cost_center = "sandbox"
  department  = "demo"
}
