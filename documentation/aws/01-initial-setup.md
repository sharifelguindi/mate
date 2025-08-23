# AWS Initial Setup

## Prerequisites

```bash
# Install required tools
brew install awscli terraform docker jq

# Verify versions
aws --version        # v2+
terraform --version  # v1.5+
docker --version
```

## AWS Account Setup

### 1. Configure AWS CLI
```bash
aws configure
# Region: us-east-1
# Output: json
```

### 2. Create Terraform Backend
```bash
# S3 bucket for state (already exists)
# Bucket: mate-terraform-state-528424611228
# DynamoDB table: mate-terraform-locks
```

## Deploy Infrastructure

### Base Infrastructure
```bash
cd infrastructure/terraform/base
terraform init
terraform plan -out=base.tfplan
terraform apply base.tfplan
```

Creates:
- VPC with 6 public/private subnets
- ECS Cluster (mate-dev)
- 3 ECR repositories (django, celery, beat)
- Cognito, WAF, KMS
- Shared EFS for ML models

### Tenant Infrastructure
```bash
cd infrastructure/terraform/tenants/demo
terraform init
terraform plan -out=tenant.tfplan
terraform apply tenant.tfplan
```

Creates per tenant:
- RDS PostgreSQL
- ElastiCache Redis
- ALB + ECS services
- S3 buckets
- EFS volumes

## Verify Deployment

```bash
# Check ECS services
aws ecs list-services --cluster mate-dev

# Check running tasks
aws ecs list-tasks --cluster mate-dev --service-name mate-demo-dev-django

# View logs
aws logs tail /ecs/mate-demo-dev/django --follow
```

## Access Application

Demo URL: https://demo.mate.sociant.ai
