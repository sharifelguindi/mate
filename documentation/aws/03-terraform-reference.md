# Terraform Module Reference

## Overview

This document provides detailed reference for all Terraform modules used in MATE's AWS infrastructure.

## Module Structure

```
infrastructure/terraform/
├── main.tf                 # Root module configuration
├── variables.tf            # Input variables
├── outputs.tf             # Output values
├── tenant.tf              # Tenant deployment configuration
├── modules/
│   ├── tenant/            # Per-tenant infrastructure
│   ├── vpc/               # Network configuration
│   ├── ecs_cluster/       # ECS cluster setup
│   ├── ecr/               # Container registry
│   ├── cognito/           # Authentication
│   ├── shared_resources/  # Shared infrastructure
│   └── waf/               # Web application firewall
└── tenants/               # Tenant-specific configurations
```

## Core Modules

### VPC Module
Creates the network infrastructure for the entire platform.

**Location**: `modules/vpc/`

**Inputs**:
- `environment` - Environment name (dev/staging/production)
- `vpc_cidr` - CIDR block for VPC (default: 10.0.0.0/16)
- `availability_zones` - List of AZs to use

**Outputs**:
- `vpc_id` - VPC identifier
- `private_subnet_ids` - List of private subnet IDs
- `public_subnet_ids` - List of public subnet IDs

### Tenant Module
Creates all infrastructure for a single tenant.

**Location**: `modules/tenant/`

**Key Variables**:
```hcl
variable "tenant_config" {
  type = object({
    tier                = string  # trial/standard/enterprise
    rds_instance_class  = string
    redis_node_type     = string
    django_desired_count = number
    # ... see modules/tenant/variables.tf for full list
  })
}
```

## Tenant Configuration

### Creating a New Tenant Configuration

Create a file in `infrastructure/terraform/tenants/[tenant-name].tfvars`:

```hcl
tenants = {
  "tenant-name" = {
    # Basic Configuration
    display_name = "Hospital Name"
    subdomain    = "hospital-subdomain"
    tier         = "enterprise"  # or "standard" or "trial"
    
    # Infrastructure Sizing
    rds_instance_class    = "db.r6g.xlarge"
    rds_allocated_storage = 100
    rds_multi_az         = true
    
    # Service Configuration
    django_desired_count = 3
    django_cpu          = 1024
    django_memory       = 2048
    
    # Compliance
    hipaa_compliant      = true
    enable_audit_logging = true
    data_retention_days  = 2555  # 7 years
    
    # Contacts
    technical_contact = "tech@hospital.com"
    billing_contact   = "billing@hospital.com"
  }
}
```

## Terraform Commands

### Initialize
```bash
terraform init
```

### Plan Changes
```bash
# For all infrastructure
terraform plan

# For specific tenant
terraform plan -var-file="tenants/hospital-a.tfvars" -target="module.tenant[\"hospital-a\"]"
```

### Apply Changes
```bash
# Apply all changes
terraform apply

# Apply specific tenant
terraform apply -var-file="tenants/hospital-a.tfvars" -target="module.tenant[\"hospital-a\"]"
```

### Destroy Resources
```bash
# WARNING: This will delete all data!
terraform destroy -var-file="tenants/hospital-a.tfvars" -target="module.tenant[\"hospital-a\"]"
```

## Customization

### Adding Custom Resources

To add custom resources to a tenant:

1. Edit `modules/tenant/main.tf` or create a new `.tf` file in the module
2. Add necessary variables to `modules/tenant/variables.tf`
3. Add outputs to `modules/tenant/outputs.tf`
4. Update tenant configurations as needed

### Modifying Tier Defaults

Edit the `tier_defaults` local variable in `modules/tenant/main.tf`:

```hcl
locals {
  tier_defaults = {
    enterprise = {
      rds_instance_class = "db.r6g.xlarge"
      # ... modify as needed
    }
  }
}
```

## Best Practices

1. **Always use workspaces** for different environments
2. **Version your module calls** to prevent unexpected changes
3. **Use data sources** instead of hardcoding resource IDs
4. **Tag everything** for cost tracking and organization
5. **Enable deletion protection** on production resources

## Troubleshooting

### State Lock Issues
```bash
terraform force-unlock <lock-id>
```

### Import Existing Resources
```bash
terraform import module.tenant[\"hospital-a\"].aws_rds_instance.tenant hospital-a-db
```

### View State
```bash
terraform state list
terraform state show module.tenant[\"hospital-a\"].aws_rds_instance.tenant
```

## Further Reading

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)