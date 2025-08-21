# AWS Multi-Tenant Deployment Guide

## Architecture Overview

MATE uses AWS-native multi-tenant architecture where each hospital/clinic gets isolated AWS resources:

- **ECS Fargate**: Serverless container hosting for Django, Celery, and Beat
- **RDS PostgreSQL**: Dedicated database per tenant (or shared for trials)
- **ElastiCache Redis**: Dedicated Redis cluster per tenant
- **S3**: Isolated bucket for each tenant's data
- **Cognito**: Centralized authentication with SSO support
- **CloudWatch**: Logging and monitoring per tenant
- **ALB**: Load balancer per tenant with custom subdomain

## Infrastructure Tiers

### Enterprise Tier
- Dedicated RDS cluster (Multi-AZ)
- Redis cluster with failover
- Auto-scaling (2-10 instances)
- EFS with provisioned throughput
- Full HIPAA compliance features

### Standard Tier
- Single RDS instance
- Single Redis node
- Auto-scaling (1-5 instances)
- EFS with burst mode
- HIPAA compliant

### Trial Tier
- Shared RDS instance
- Shared Redis instance
- Fixed single instance
- Limited storage
- Basic features only

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Tools installed**:
   ```bash
   # AWS CLI
   brew install awscli

   # Terraform
   brew install terraform

   # Docker
   brew install --cask docker

   # jq for JSON processing
   brew install jq
   ```

3. **AWS Configuration**:
   ```bash
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Default region: us-east-1
   # Default output format: json
   ```

## Initial Setup

### 1. Create Terraform Backend

```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket mate-terraform-state \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket mate-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name mate-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

### 2. Configure Base Infrastructure

```bash
cd infrastructure/terraform

# Copy and edit terraform variables
cp terraform.tfvars.example terraform.tfvars
# Edit with your values:
# - domain_name
# - cognito_domain
# - environment

# Initialize Terraform
terraform init

# Deploy base infrastructure (VPC, ECS Cluster, ECR, etc.)
terraform plan
terraform apply
```

### 3. Build and Push Docker Images

```bash
# Get ECR registry URL
export ECR_REGISTRY=$(terraform output -raw ecr_registry)

# Build and push images
./scripts/deploy.sh build
```

## Provisioning a New Tenant

### Automated Provisioning

```bash
# Run the provisioning script
./scripts/provision-tenant.sh

# Follow the prompts:
# - Tenant name: hospital-a
# - Display name: Hospital A Medical Center
# - Tier: enterprise
# - Contact email: admin@hospitala.com
# - SSO configuration: saml
```

### Manual Provisioning

1. **Create Terraform configuration**:
```hcl
# infrastructure/terraform/tenants/hospital-a.tfvars
tenants = {
  "hospital-a" = {
    display_name = "Hospital A Medical Center"
    subdomain    = "hospital-a"
    tier         = "enterprise"

    # ... additional configuration
  }
}
```

2. **Deploy infrastructure**:
```bash
cd infrastructure/terraform
terraform plan -var-file="tenants/hospital-a.tfvars"
terraform apply -var-file="tenants/hospital-a.tfvars"
```

3. **Run migrations**:
```bash
./scripts/deploy.sh migrate hospital-a
```

4. **Deploy services**:
```bash
./scripts/deploy.sh tenant hospital-a
```

## Managing Tenants

### Update a Tenant's Service

```bash
# Update Django service
./scripts/deploy.sh update-service hospital-a django

# Update Celery workers
./scripts/deploy.sh update-service hospital-a celery
```

### Scale a Tenant

```bash
# Edit the tenant configuration
vim infrastructure/terraform/tenants/hospital-a.tfvars
# Change django_desired_count, celery_desired_count

# Apply changes
cd infrastructure/terraform
terraform apply -var-file="tenants/hospital-a.tfvars"
```

### Suspend a Tenant

```bash
# Set desired count to 0 in configuration
# Or use AWS Console to stop ECS services
aws ecs update-service \
  --cluster mate-production \
  --service mate-hospital-a-production-django \
  --desired-count 0
```

## Monitoring

### CloudWatch Dashboards

Each tenant has dedicated CloudWatch dashboards:
- `mate-hospital-a-production` - Main metrics
- `/ecs/mate-hospital-a-production/*` - Application logs
- RDS Performance Insights for database monitoring

### Key Metrics to Monitor

1. **ECS Metrics**:
   - CPU Utilization
   - Memory Utilization
   - Task count
   - Request count/latency

2. **RDS Metrics**:
   - CPU Utilization
   - Database connections
   - Storage space
   - Read/Write IOPS

3. **ElastiCache Metrics**:
   - CPU Utilization
   - Memory usage
   - Cache hits/misses
   - Network throughput

## Security Considerations

### HIPAA Compliance

- All data encrypted at rest (KMS)
- All data encrypted in transit (TLS)
- Audit logging enabled
- VPC isolation per environment
- IAM roles with least privilege
- Secrets in AWS Secrets Manager

### Network Security

- Private subnets for all services
- ALB with WAF protection
- Security groups with minimal access
- NACLs for additional protection
- VPC Flow Logs for audit

## Disaster Recovery

### Backup Strategy

1. **RDS Automated Backups**:
   - Daily snapshots
   - 30-day retention (enterprise)
   - Point-in-time recovery

2. **S3 Versioning**:
   - All tenant buckets versioned
   - Lifecycle policies for archival

3. **Infrastructure as Code**:
   - All infrastructure in Terraform
   - State backed up in S3

### Recovery Procedures

```bash
# Restore RDS from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier mate-hospital-a-production-restored \
  --db-snapshot-identifier <snapshot-id>

# Restore S3 data
aws s3 sync s3://mate-hospital-a-backup s3://mate-hospital-a-production-data

# Redeploy infrastructure
terraform apply -var-file="tenants/hospital-a.tfvars"
```

## Cost Optimization

### Recommendations

1. **Use Savings Plans** for predictable workloads
2. **Reserved Instances** for RDS (1-3 year terms)
3. **S3 Intelligent-Tiering** for automatic cost optimization
4. **Auto-scaling** to match demand
5. **Spot Instances** for non-critical Celery workers

### Cost Monitoring

```bash
# Set up billing alerts
aws cloudwatch put-metric-alarm \
  --alarm-name mate-billing-alarm \
  --alarm-description "Alert when costs exceed $1000" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold
```

## Troubleshooting

### Common Issues

1. **ECS Task Fails to Start**:
```bash
# Check task logs
aws ecs describe-tasks \
  --cluster mate-production \
  --tasks <task-arn>

# Check CloudWatch logs
aws logs tail /ecs/mate-hospital-a-production/django --follow
```

2. **Database Connection Issues**:
```bash
# Check security groups
aws ec2 describe-security-groups --group-ids <sg-id>

# Test connectivity
aws ecs run-task \
  --cluster mate-production \
  --task-definition mate-hospital-a-production-django \
  --overrides '{"containerOverrides":[{"name":"django","command":["python","manage.py","dbshell"]}]}'
```

3. **High Memory Usage**:
```bash
# Scale up task definition
# Edit infrastructure/terraform/modules/tenant/ecs.tf
# Increase memory values and redeploy
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to ECS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Build and push Docker images
        run: |
          ./scripts/deploy.sh build

      - name: Deploy to ECS
        run: |
          ./scripts/deploy.sh all
```

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review Terraform state
3. Contact the DevOps team
4. Create an issue in the repository
