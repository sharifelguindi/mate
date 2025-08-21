# Base infrastructure configuration
# This creates the shared resources for all tenants

environment         = "dev"
aws_region         = "us-east-1"
vpc_cidr           = "10.0.0.0/16"
domain_name        = "mate.sociant.ai"
create_route53_zone = false
cognito_domain     = "mate-sociant-auth"
cost_center        = "engineering"
enable_deletion_protection = false