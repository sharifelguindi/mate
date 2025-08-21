terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Each tenant has its own state file
  backend "s3" {
    bucket         = "mate-terraform-state-528424611228"
    key            = "tenants/demo/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "mate-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Project     = "MATE"
      Tenant      = var.tenant_name
    }
  }
}

# Read outputs from base infrastructure
data "terraform_remote_state" "base" {
  backend = "s3"
  config = {
    bucket = "mate-terraform-state-528424611228"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-1"
  }
}

# Deploy the tenant module
module "tenant" {
  source = "../../base/modules/tenant"
  
  # Tenant configuration
  tenant_name   = var.tenant_name
  tenant_config = var.tenant_config
  environment   = var.environment
  
  # Reference base infrastructure
  vpc_id             = data.terraform_remote_state.base.outputs.vpc_id
  private_subnet_ids = data.terraform_remote_state.base.outputs.private_subnet_ids
  public_subnet_ids  = data.terraform_remote_state.base.outputs.public_subnet_ids
  ecs_cluster_id     = data.terraform_remote_state.base.outputs.ecs_cluster_id
  ecs_cluster_name   = data.terraform_remote_state.base.outputs.ecs_cluster_name
  kms_key_id        = data.terraform_remote_state.base.outputs.kms_key_id
  
  # ECR repositories
  ecr_repositories = data.terraform_remote_state.base.outputs.ecr_repositories
  
  # Cognito configuration
  cognito_user_pool_id      = data.terraform_remote_state.base.outputs.cognito_user_pool_id
  cognito_user_pool_domain  = data.terraform_remote_state.base.outputs.cognito_user_pool_domain
  cognito_app_client_id     = data.terraform_remote_state.base.outputs.cognito_app_client_id
  cognito_app_client_secret = data.terraform_remote_state.base.outputs.cognito_app_client_secret
  
  # Domain configuration
  domain_name      = data.terraform_remote_state.base.outputs.domain_name
  certificate_arn  = data.terraform_remote_state.base.outputs.certificate_arn
  route53_zone_id  = data.terraform_remote_state.base.outputs.route53_zone_id
  
  # WAF configuration
  waf_web_acl_id = data.terraform_remote_state.base.outputs.waf_web_acl_id
  
  # Shared EFS for base AI models
  shared_models_efs_id = data.terraform_remote_state.base.outputs.shared_models_efs_id
  
  aws_region = var.aws_region
}