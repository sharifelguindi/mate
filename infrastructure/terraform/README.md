# MATE Infrastructure - Terraform

This infrastructure uses a **separated deployment model** where base infrastructure and tenants are deployed independently.

## Directory Structure

```
terraform/
├── base/                    # Shared infrastructure (deploy once)
│   ├── main.tf             # VPC, ECS Cluster, Cognito, etc.
│   ├── terraform.tfvars    # Base configuration
│   └── modules/            # All Terraform modules
│       ├── vpc/
│       ├── ecs_cluster/
│       ├── tenant/         # Tenant module used by each tenant
│       └── ...
└── tenants/                # Individual tenant deployments
    ├── demo/               # Demo hospital tenant
    │   ├── main.tf
    │   └── terraform.tfvars
    ├── hospital-a/         # Future tenant
    └── template/           # Template for new tenants
```

## Deployment Process

### 1. Deploy Base Infrastructure (One Time)

```bash
cd base/
terraform init
terraform plan
terraform apply
```

This creates:
- VPC with networking (~$45/month for NAT Gateway)
- ECS Cluster (pay per container)
- Shared EFS for base AI models
- Cognito, WAF, KMS, ECR repositories
- Route53 zone and SSL certificate

**Cost**: ~$52/month base

### 2. Deploy Demo Tenant

```bash
cd ../tenants/demo/
terraform init
terraform plan
terraform apply
```

This creates isolated resources for demo.mate.sociant.ai:
- RDS PostgreSQL database
- ElastiCache Redis
- S3 buckets
- EFS for tenant data and models
- ALB and ECS services

**Cost**: ~$65/month per tenant

### 3. Add New Tenants (Without Affecting Others)

```bash
# Copy template
cp -r tenants/template tenants/hospital-a

# Edit configuration
cd tenants/hospital-a
# Update main.tf: Change TENANT_NAME in backend config
# Update terraform.tfvars with hospital details

# Deploy independently
terraform init
terraform plan
terraform apply
```

## Managing Tenants

### Update Single Tenant
```bash
cd tenants/demo
terraform apply  # Only affects demo tenant
```

### Remove Tenant
```bash
cd tenants/demo
terraform destroy  # Only removes demo resources
```

### View Tenant Costs
```bash
cd tenants/demo
terraform show  # Shows all resources for billing
```

## Tenant Isolation

Each tenant gets completely isolated:
- **Database**: Separate RDS instance
- **Cache**: Separate Redis cluster
- **Storage**: Separate S3 buckets
- **Compute**: Separate ECS services
- **Models**: Own EFS + access to shared base models

## Cost Optimization

### Development (Destroy when not testing)
```bash
# Destroy demo to save money
cd tenants/demo
terraform destroy

# Keep base infrastructure (only $52/month)
```

### Production
- Use auto-scaling for larger tenants
- Enable Multi-AZ for critical hospitals
- Use reserved instances for predictable workloads

## Tenant Tiers

### Starter (Free/$99/month)
```hcl
django_cpu = 256
django_memory = 512
rds_instance_class = "db.t4g.micro"
```

### Professional ($1000/month revenue)
```hcl
django_desired_count = 2
enable_autoscaling = true
rds_multi_az = true
```

### Enterprise ($8000+/month revenue)
```hcl
django_desired_count = 10
django_cpu = 2048
rds_instance_class = "db.r6g.xlarge"
```

## Important Notes

1. **State Files**: Each tenant has its own Terraform state in S3
2. **Dependencies**: Base infrastructure must exist before deploying tenants
3. **Parallel Deployments**: Multiple tenants can be deployed simultaneously
4. **Zero Downtime**: Updating one tenant doesn't affect others
5. **Rollback**: Each tenant can be rolled back independently
