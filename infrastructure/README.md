# MATE Infrastructure

## Architecture Overview

Multi-tenant SaaS infrastructure using Terraform with AWS ECS Fargate.

### Stack
- **IaC**: Terraform v1.5+ (modular design)
- **Container Platform**: ECS Fargate
- **Database**: RDS PostgreSQL per tenant
- **Cache**: ElastiCache Redis per tenant
- **Storage**: S3 + EFS
- **Load Balancing**: ALB with SSL
- **CI/CD**: GitHub Actions

## Directory Structure

```
infrastructure/
├── ecs/                    # ECS task definitions and services
├── iam/                    # IAM policies for deployment
├── terraform/
│   ├── base/              # Shared infrastructure
│   │   └── modules/       # Reusable Terraform modules
│   └── tenants/           # Per-tenant configurations
│       ├── demo/          # Demo environment
│       └── template/      # Template for new tenants
```

## Terraform Commands

### Initial Setup
```bash
# Initialize Terraform (download providers, setup backend)
terraform init

# Format code to canonical style
terraform fmt -recursive

# Validate configuration syntax
terraform validate
```

### Planning & Deployment
```bash
# Preview changes before applying (RECOMMENDED)
terraform plan

# Save plan to file for safer apply (BEST PRACTICE)
terraform plan -out=tfplan
terraform apply tfplan

# Apply changes interactively
terraform apply

# Apply with auto-approval (USE WITH CAUTION)
terraform apply -auto-approve

# Apply specific target only (EXCEPTIONAL USE - see warning below)
terraform apply -target=module.tenant.aws_ecs_service.django

# Destroy specific resource (EXCEPTIONAL USE)
terraform destroy -target=module.tenant.aws_ecs_service.django
```

⚠️ **Note on -target**: The `-target` flag is for exceptional situations like:
- Recovering from errors
- Debugging specific resources
- When Terraform suggests it in an error message

For routine updates, always use full `terraform plan` and `terraform apply` without targeting.

### State Management
```bash
# List all resources in state
terraform state list

# Show specific resource details
terraform state show module.tenant.aws_ecs_service.django

# Pull current state from backend
terraform state pull > current-state.json

# Remove resource from state (doesn't delete actual resource)
terraform state rm module.tenant.aws_ecs_service.django

# Move resource in state
terraform state mv aws_instance.old aws_instance.new

# Replace resource (force recreation)
terraform apply -replace="module.tenant.aws_ecs_service.django"
```

### Inspection & Debugging
```bash
# Show output values
terraform output
terraform output -json

# Show specific output
terraform output alb_dns_name

# Generate dependency graph
terraform graph | dot -Tpng > graph.png

# Show provider requirements
terraform providers

# Debug with detailed logs
TF_LOG=DEBUG terraform plan
TF_LOG=TRACE terraform apply
```

### Workspace Management
```bash
# List workspaces
terraform workspace list

# Create and switch to new workspace
terraform workspace new staging
terraform workspace select staging

# Delete workspace
terraform workspace delete staging
```

### Import Existing Resources
```bash
# Import existing AWS resource into Terraform
terraform import module.tenant.aws_s3_bucket.data mate-demo-dev-data

# Generate configuration for imported resource
terraform show -no-color > imported.tf
```

### Base Infrastructure Deployment
```bash
cd terraform/base
terraform init
terraform plan -out=base.tfplan
terraform apply base.tfplan
```

### Tenant Infrastructure Deployment
```bash
cd terraform/tenants/demo
terraform init
terraform plan -var="environment=dev" -out=tenant.tfplan
terraform apply tenant.tfplan

# Destroy tenant (preserves base infrastructure)
terraform destroy -auto-approve
```

## Tenant Tiers

| Tier | RDS | Redis | ECS Resources |
|------|-----|-------|---------------|
| Trial | db.t4g.micro | cache.t4g.micro | 256 CPU / 512 MB |
| Standard | db.t4g.medium | cache.t4g.small | 512 CPU / 1024 MB |
| Enterprise | db.r6g.xlarge | cache.r7g.large | 1024 CPU / 2048 MB |

## Key Features

- **Tenant Isolation**: Separate RDS, Redis, S3 per tenant
- **Security**: KMS encryption, Secrets Manager, WAF
- **Monitoring**: CloudWatch logs and metrics
- **Auto-scaling**: ECS service scaling based on metrics
- **Cost Optimization**: Tiered resources, shared ECS cluster

## Current Status

✅ **Working**
- All services (Django, Celery, Beat) running
- ALB health checks passing
- Database and Redis connections established
- CI/CD pipeline deploying from dev branch

⚠️ **Known Issues**
- No automated Terraform in CI/CD
- Basic monitoring only

## Troubleshooting

### Common Terraform Commands
```bash
# Refresh state with actual infrastructure
terraform refresh

# Unlock state if locked (use with caution)
terraform force-unlock <lock-id>

# Check what Terraform manages
terraform state list | grep -i django

# Download and inspect remote state
terraform state pull | jq '.resources[] | select(.type == "aws_ecs_service")'

# Cost estimation (requires Infracost)
infracost breakdown --path .

# Security scanning
tfsec .
checkov -d .
```

### AWS Resource Inspection
```bash
# Check ECS services
aws ecs list-services --cluster mate-dev
aws ecs describe-services --cluster mate-dev --services mate-demo-dev-django

# View running tasks
aws ecs list-tasks --cluster mate-dev --service-name mate-demo-dev-django
aws ecs describe-tasks --cluster mate-dev --tasks <task-arn>

# Check CloudWatch logs
aws logs tail /ecs/mate-demo-dev/django --follow

# Force new deployment
aws ecs update-service --cluster mate-dev --service mate-demo-dev-django --force-new-deployment
```

## Support

- **Demo URL**: https://demo.mate.sociant.ai
- **State Bucket**: s3://mate-terraform-state-528424611228
- **AWS Region**: us-east-1