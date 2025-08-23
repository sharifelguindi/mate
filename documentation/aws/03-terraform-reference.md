# Terraform Reference

## Module Structure

```
infrastructure/terraform/
├── base/                  # Shared infrastructure
│   ├── main.tf
│   └── modules/
│       ├── vpc/          # Network
│       ├── ecs_cluster/  # ECS cluster
│       ├── ecr/          # Container registry
│       ├── cognito/      # Authentication
│       └── tenant/       # Tenant resources
└── tenants/              # Per-tenant configs
    └── demo/
```

## Tenant Configuration

Example `terraform.tfvars`:
```hcl
tenant_name = "demo"
tenant_config = {
  display_name = "Demo Hospital"
  subdomain    = "demo"
  tier         = "trial"

  # Resources
  rds_instance_class = "db.t4g.micro"
  redis_node_type    = "cache.t4g.micro"

  # ECS
  django_cpu    = 256
  django_memory = 512
}
```

## Tier Specifications

| Tier | RDS | Redis | ECS CPU/Memory |
|------|-----|-------|----------------|
| Trial | db.t4g.micro | cache.t4g.micro | 256/512 |
| Standard | db.t4g.medium | cache.t4g.small | 512/1024 |
| Enterprise | db.r6g.xlarge | cache.r7g.large | 1024/2048 |

## Common Operations

```bash
# Add new tenant
cd infrastructure/terraform/tenants
cp -r template new-tenant
# Edit new-tenant/main.tf and terraform.tfvars
terraform init
terraform apply

# Update tenant resources
terraform apply -var="django_cpu=512"

# Remove tenant
terraform destroy
```
