terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket      = "mate-terraform-state-528424611228"
    key         = "infrastructure/terraform.tfstate"
    region      = "us-east-1"
    encrypt     = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Project     = "MATE"
      CostCenter  = var.cost_center
    }
  }
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# Data sources for existing resources
data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# KMS key for encryption
resource "aws_kms_key" "main" {
  description             = "KMS key for MATE ${var.environment}"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          ArnLike = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:*"
          }
        }
      }
    ]
  })

  tags = {
    Name = "mate-${var.environment}-kms"
  }
}

resource "aws_kms_alias" "main" {
  name          = "alias/mate-${var.environment}"
  target_key_id = aws_kms_key.main.key_id
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  environment         = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = data.aws_availability_zones.available.names
  kms_key_id        = aws_kms_key.main.id
}

# ECS Cluster
module "ecs_cluster" {
  source = "./modules/ecs_cluster"

  environment = var.environment
  kms_key_id  = aws_kms_key.main.id

  enable_container_insights = true  # Enable for all environments for better monitoring
}

# ECR Repositories
module "ecr" {
  source = "./modules/ecr"

  environment = var.environment
  kms_key_id  = aws_kms_key.main.arn

  repositories = [
    "mate-django",
    "mate-celery",
    "mate-beat"
  ]
}

# Shared Resources (used by all tenants)
module "shared_resources" {
  source = "./modules/shared_resources"

  environment        = var.environment
  vpc_id            = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  kms_key_id        = aws_kms_key.main.arn
}

# Cognito User Pool for authentication
module "cognito" {
  source = "./modules/cognito"

  environment = var.environment
  kms_key_id  = aws_kms_key.main.arn
  domain      = var.cognito_domain
}

# WAF for API protection
module "waf" {
  source = "./modules/waf"

  environment = var.environment
}

# Route53 Hosted Zone
data "aws_route53_zone" "main" {
  count = var.create_route53_zone ? 0 : 1
  name  = var.domain_name
}

resource "aws_route53_zone" "main" {
  count = var.create_route53_zone ? 1 : 0
  name  = var.domain_name

  tags = {
    Name = "mate-${var.environment}"
  }
}

locals {
  zone_id = var.create_route53_zone ? aws_route53_zone.main[0].zone_id : data.aws_route53_zone.main[0].zone_id
}

# ACM Certificate for HTTPS
resource "aws_acm_certificate" "main" {
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "mate-${var.environment}"
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = local.zone_id
}

resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# Outputs are defined in outputs.tf
