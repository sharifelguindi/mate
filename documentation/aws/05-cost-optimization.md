# Cost Optimization

## Current Costs

### Base Infrastructure
- NAT Gateway: ~$45/month
- ECS Cluster: $0 (pay per container)
- Route53: ~$0.50/month
- KMS: ~$1/month
- **Total Base**: ~$52/month

### Per Tenant (Demo)
- RDS (db.t4g.micro): ~$15/month
- Redis (cache.t4g.micro): ~$15/month
- ECS Tasks: ~$15/month
- ALB: ~$20/month
- Storage: ~$5/month
- **Total per Tenant**: ~$70/month

## Optimization Strategies

### 1. Right-Size Resources
```bash
# Monitor actual usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=mate-demo-dev-django \
  --period 3600 --statistics Average \
  --start-time $(date -u -d '7 days ago' --iso-8601) \
  --end-time $(date --iso-8601)

# Adjust in terraform.tfvars if overprovisioned
django_cpu = 256     # Reduce if CPU < 40%
django_memory = 512  # Reduce if memory < 50%
```

### 2. Use Spot Instances
```hcl
# In modules/tenant/ecs.tf for non-critical services
capacity_provider_strategy {
  capacity_provider = "FARGATE_SPOT"
  weight = 80
}
```

### 3. Schedule Non-Production
```bash
# Stop development environment at night
aws ecs update-service --cluster mate-dev \
  --service mate-demo-dev-django \
  --desired-count 0

# Restart in morning
aws ecs update-service --cluster mate-dev \
  --service mate-demo-dev-django \
  --desired-count 1
```

### 4. Reserved Capacity
For production workloads with predictable usage:
- RDS Reserved Instances: Save ~30%
- Savings Plans for Compute: Save ~20%

## Cost Monitoring

```bash
# Set budget alert
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget BudgetName=MATE,BudgetLimit={Amount=200,Unit=USD},TimeUnit=MONTHLY \
  --notifications-with-subscribers NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80,ThresholdType=PERCENTAGE,SubscriberEmailAddresses=admin@example.com
```
