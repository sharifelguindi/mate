# AWS Cost Optimization Guide

## Overview

This guide provides strategies for optimizing AWS costs while maintaining performance and compliance for MATE deployments.

## Cost Monitoring

### Setting Up Cost Tracking

#### Enable Cost Allocation Tags
```bash
# Tag all resources with tenant information
aws tag-resources \
  --resource-arn-list <arns> \
  --tags Tenant=hospital-a,Environment=production,CostCenter=healthcare
```

#### Create Cost and Usage Reports
```bash
aws cur put-report-definition \
  --report-definition '{
    "ReportName": "mate-cost-report",
    "TimeUnit": "DAILY",
    "Format": "textORcsv",
    "Compression": "GZIP",
    "S3Bucket": "mate-cost-reports",
    "S3Prefix": "reports",
    "S3Region": "us-east-1",
    "AdditionalSchemaElements": ["RESOURCES"],
    "AdditionalArtifacts": ["QUICKSIGHT"]
  }'
```

### Cost Dashboards

#### CloudWatch Dashboard for Costs
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Billing", "EstimatedCharges", {"stat": "Maximum"}]
        ],
        "period": 86400,
        "stat": "Maximum",
        "region": "us-east-1",
        "title": "Daily Estimated Charges"
      }
    }
  ]
}
```

## Cost Optimization by Service

### ECS Fargate

#### Right-sizing Containers
```hcl
# Start conservative, monitor, then adjust
# Trial tier
django_cpu    = 256   # 0.25 vCPU
django_memory = 512   # 0.5 GB

# After monitoring, if CPU < 40% average:
django_cpu    = 256
django_memory = 512

# If CPU > 70% average:
django_cpu    = 512
django_memory = 1024
```

#### Fargate Spot for Non-Critical Workloads
```hcl
resource "aws_ecs_service" "celery" {
  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 80
  }
  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 20
  }
}
```

### RDS Optimization

#### Reserved Instances
```bash
# Check recommendations
aws ce get-reservation-purchase-recommendation \
  --service "Amazon Relational Database Service" \
  --account-scope PAYER \
  --lookback-period-in-days SIXTY_DAYS \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT
```

#### Instance Type by Tier
```hcl
# Cost-optimized instance selection
locals {
  rds_instance_map = {
    trial      = "db.t4g.micro"     # ~$13/month
    standard   = "db.t4g.medium"    # ~$52/month
    enterprise = "db.r6g.xlarge"    # ~$506/month
  }
}
```

#### Automated Start/Stop for Non-Production
```python
# Lambda function to stop RDS at night
import boto3

def lambda_handler(event, context):
    rds = boto3.client('rds')
    
    # Stop non-production databases
    for db in ['mate-dev-db', 'mate-staging-db']:
        try:
            rds.stop_db_instance(DBInstanceIdentifier=db)
        except Exception as e:
            print(f"Error stopping {db}: {e}")
```

### S3 Cost Optimization

#### Intelligent Tiering
```bash
# Enable Intelligent-Tiering
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket mate-hospital-a-data \
  --id ArchiveConfig \
  --intelligent-tiering-configuration '{
    "Id": "ArchiveConfig",
    "Status": "Enabled",
    "Tierings": [
      {
        "Days": 90,
        "AccessTier": "ARCHIVE_ACCESS"
      },
      {
        "Days": 180,
        "AccessTier": "DEEP_ARCHIVE_ACCESS"
      }
    ]
  }'
```

#### Lifecycle Policies
```json
{
  "Rules": [
    {
      "Id": "DeleteOldLogs",
      "Status": "Enabled",
      "Expiration": {
        "Days": 90
      },
      "Filter": {
        "Prefix": "logs/"
      }
    },
    {
      "Id": "ArchiveOldData",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

### ElastiCache Optimization

#### Node Type Selection
```hcl
# Cost vs Performance
locals {
  redis_node_map = {
    trial      = "cache.t4g.micro"   # ~$12/month
    standard   = "cache.t4g.small"   # ~$24/month
    enterprise = "cache.r7g.large"   # ~$142/month
  }
}
```

## Savings Plans & Reserved Capacity

### Compute Savings Plans
```bash
# Get recommendations
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days THIRTY_DAYS
```

### Coverage Targets
- Development: 0% (use on-demand)
- Staging: 50% coverage
- Production: 75-85% coverage

## Cost Allocation by Tenant

### Tagging Strategy
```hcl
locals {
  common_tags = {
    Project     = "MATE"
    Environment = var.environment
    Tenant      = var.tenant_name
    CostCenter  = var.tenant_config.cost_center
    ManagedBy   = "Terraform"
  }
}
```

### Monthly Tenant Reports
```python
import boto3
import pandas as pd
from datetime import datetime, timedelta

def generate_tenant_cost_report(tenant_name):
    ce = boto3.client('ce')
    
    end = datetime.now().date()
    start = end - timedelta(days=30)
    
    response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': start.isoformat(),
            'End': end.isoformat()
        },
        Granularity='DAILY',
        Metrics=['UnblendedCost'],
        Filter={
            'Tags': {
                'Key': 'Tenant',
                'Values': [tenant_name]
            }
        },
        GroupBy=[
            {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        ]
    )
    
    return pd.DataFrame(response['ResultsByTime'])
```

## Budget Alerts

### Create Budgets per Tenant
```bash
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget '{
    "BudgetName": "mate-hospital-a-monthly",
    "BudgetLimit": {
      "Amount": "5000",
      "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
      "TagKeyValue": ["user:Tenant$hospital-a"]
    }
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {
          "SubscriptionType": "EMAIL",
          "Address": "billing@hospital-a.com"
        }
      ]
    }
  ]'
```

## Cost Optimization Checklist

### Daily
- [ ] Review CloudWatch cost anomaly detector
- [ ] Check for unused ECS tasks

### Weekly
- [ ] Review RDS and ElastiCache metrics for right-sizing
- [ ] Check for unattached EBS volumes
- [ ] Review S3 bucket sizes

### Monthly
- [ ] Generate tenant cost reports
- [ ] Review Reserved Instance utilization
- [ ] Analyze cost trends
- [ ] Update budgets if needed

### Quarterly
- [ ] Review Savings Plans recommendations
- [ ] Evaluate tier assignments (trial → standard → enterprise)
- [ ] Audit and remove unused resources

## Cost Reduction Quick Wins

### Immediate Savings (No Impact)
1. **Delete unattached EBS volumes**
   ```bash
   aws ec2 describe-volumes --filters Name=status,Values=available
   ```

2. **Remove old snapshots**
   ```bash
   aws ec2 describe-snapshots --owner-ids self \
     --query 'Snapshots[?StartTime<=`2023-01-01`]'
   ```

3. **Clean up old ECR images**
   ```bash
   aws ecr put-lifecycle-policy \
     --repository-name mate-web \
     --lifecycle-policy-text '{
       "rules": [{
         "rulePriority": 1,
         "selection": {
           "tagStatus": "untagged",
           "countType": "imageCountMoreThan",
           "countNumber": 10
         },
         "action": {"type": "expire"}
       }]
     }'
   ```

### Medium-term Savings
1. Purchase Reserved Instances for stable workloads
2. Implement auto-scaling for variable loads
3. Use Spot instances for batch processing

### Long-term Strategy
1. Optimize architecture for serverless where appropriate
2. Implement FinOps practices
3. Regular architecture reviews for cost efficiency

## Cost Calculators

### Estimate Tenant Costs
```python
def estimate_monthly_cost(tier, region='us-east-1'):
    costs = {
        'trial': {
            'ecs': 20,      # Shared resources
            'rds': 0,       # Shared RDS
            'redis': 0,     # Shared Redis
            's3': 5,
            'alb': 20,
            'total': 45
        },
        'standard': {
            'ecs': 80,      # 2 tasks
            'rds': 52,      # t4g.medium
            'redis': 24,    # t4g.small
            's3': 20,
            'alb': 20,
            'data_transfer': 10,
            'total': 206
        },
        'enterprise': {
            'ecs': 320,     # 6 tasks
            'rds': 506,     # r6g.xlarge
            'redis': 142,   # r7g.large
            's3': 100,
            'alb': 20,
            'data_transfer': 50,
            'backup': 50,
            'total': 1188
        }
    }
    
    return costs.get(tier, {})
```

## Resources

- [AWS Pricing Calculator](https://calculator.aws/)
- [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/)