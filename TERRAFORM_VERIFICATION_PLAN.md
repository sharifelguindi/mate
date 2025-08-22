# Terraform and CI/CD Verification Plan

## Overview
This plan verifies the Terraform infrastructure aligns with CI/CD pipeline requirements for dev and staging branches, then destroys and recreates the demo tenant to ensure a clean, working deployment system.

## Current State Analysis

### Base Infrastructure (Already Deployed)
- **VPC and Networking**: 6 subnets across availability zones
- **ECS Cluster**: `mate-dev` cluster with Fargate capacity providers
- **ECR Repositories**: mate-django, mate-celery, mate-beat, mate-web
- **Shared Resources**: EFS for shared models, CloudWatch log groups
- **Cognito**: User pool and client for authentication
- **ACM Certificate**: SSL for *.mate.sociant.ai and mate.sociant.ai
- **KMS**: Encryption key for resources

### Demo Tenant (Currently Deployed)
- **RDS PostgreSQL**: Database instance for tenant
- **ElastiCache Redis**: Cache cluster for tenant
- **ECS Services**: django, celery, beat services
- **EFS Access Points**: Tenant-specific data storage
- **IAM Roles**: Task execution and task roles
- **Security Groups**: Network access controls
- **Secrets Manager**: Database and Redis credentials

### CI/CD Pipeline Configuration
The pipeline deploys to different environments based on branch:
- **main branch** → production environment
- **staging branch** → dev environment (Note: confusing naming)
- **dev branch** → dev environment

Key pipeline expectations:
1. **ECR Image Tags**: Uses git SHA for image tags
2. **ECS Task Definitions**: `mate-demo-${ENVIRONMENT}-${SERVICE}`
3. **ECS Cluster**: `mate-${ENVIRONMENT}`
4. **Services**: django, celery, beat
5. **Migration Task**: Runs as one-off ECS task before deployment

## Verification Steps

### Step 1: Pre-Destruction Verification
```bash
# 1.1 Check current ECS services status
aws ecs list-services --cluster mate-dev --output json | jq '.serviceArns'

# 1.2 Check current task definitions
aws ecs list-task-definitions --family-prefix mate-demo-dev --output json | jq '.taskDefinitionArns'

# 1.3 Verify RDS instance
aws rds describe-db-instances --db-instance-identifier mate-demo-dev --query 'DBInstances[0].DBInstanceStatus'

# 1.4 Verify ElastiCache cluster
aws elasticache describe-cache-clusters --cache-cluster-id mate-demo-dev-redis --query 'CacheClusters[0].CacheClusterStatus'

# 1.5 Check ALB health
aws elbv2 describe-target-health --target-group-arn $(aws elbv2 describe-target-groups --names mate-demo-dev-django --query 'TargetGroups[0].TargetGroupArn' --output text)

# 1.6 Save current Terraform outputs
cd /Users/elguinds/PycharmProjects/mate/infrastructure/terraform/tenants/demo
terraform output -json > demo-tenant-outputs-backup.json
```

### Step 2: Destroy Demo Tenant
```bash
# 2.1 Navigate to demo tenant directory
cd /Users/elguinds/PycharmProjects/mate/infrastructure/terraform/tenants/demo

# 2.2 Plan the destruction (review what will be destroyed)
terraform plan -destroy -out=destroy.tfplan

# 2.3 Destroy the tenant infrastructure
terraform apply destroy.tfplan

# 2.4 Verify destruction
aws ecs list-services --cluster mate-dev | grep demo  # Should return empty
aws rds describe-db-instances --db-instance-identifier mate-demo-dev  # Should fail
```

### Step 3: Recreate Demo Tenant
```bash
# 3.1 Update terraform.tfvars if needed
cat > terraform.tfvars <<EOF
tenant_name = "demo"
environment = "dev"
tenant_subdomain = "demo"

# Database configuration
db_instance_class = "db.t3.micro"
db_allocated_storage = 20
db_backup_retention_period = 7

# Redis configuration
redis_node_type = "cache.t3.micro"
redis_num_cache_nodes = 1

# ECS configuration
ecs_desired_count = {
  django = 1
  celery = 1
  beat   = 1
}

ecs_cpu = {
  django = 512
  celery = 256
  beat   = 256
}

ecs_memory = {
  django = 1024
  celery = 512
  beat   = 512
}

# Tags
tags = {
  Tenant = "demo"
  Environment = "dev"
  ManagedBy = "terraform"
}
EOF

# 3.2 Initialize and plan
terraform init
terraform plan -out=create.tfplan

# 3.3 Apply the configuration
terraform apply create.tfplan

# 3.4 Save outputs
terraform output -json > demo-tenant-outputs.json
```

### Step 4: Verify ECS Task Definitions Alignment
```bash
# 4.1 Check task definition compatibility with CI/CD
for service in django celery beat; do
  echo "Checking $service task definition..."
  aws ecs describe-task-definition \
    --task-definition mate-demo-dev-$service \
    --query 'taskDefinition.{family:family,cpu:cpu,memory:memory,networkMode:networkMode}' \
    --output json
done

# 4.2 Verify task definitions use correct image repositories
for service in django celery beat; do
  aws ecs describe-task-definition \
    --task-definition mate-demo-dev-$service \
    --query 'taskDefinition.containerDefinitions[0].image' \
    --output text
done
```

### Step 5: Initial Docker Image Build & Push
```bash
# 5.1 Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 528424611228.dkr.ecr.us-east-1.amazonaws.com

# 5.2 Build production image
cd /Users/elguinds/PycharmProjects/mate
docker build -f compose/production/django/Dockerfile -t mate-django:latest .

# 5.3 Tag and push for each service with 'latest' tag
for service in django celery beat; do
  docker tag mate-django:latest 528424611228.dkr.ecr.us-east-1.amazonaws.com/mate-$service:latest
  docker push 528424611228.dkr.ecr.us-east-1.amazonaws.com/mate-$service:latest
done

# 5.4 Also tag with git SHA for CI/CD compatibility
GIT_SHA=$(git rev-parse --short HEAD)
for service in django celery beat; do
  docker tag mate-django:latest 528424611228.dkr.ecr.us-east-1.amazonaws.com/mate-$service:$GIT_SHA
  docker push 528424611228.dkr.ecr.us-east-1.amazonaws.com/mate-$service:$GIT_SHA
done
```

### Step 6: Update ECS Services with Initial Images
```bash
# 6.1 Force new deployment with latest images
for service in django celery beat; do
  aws ecs update-service \
    --cluster mate-dev \
    --service mate-demo-dev-$service \
    --force-new-deployment \
    --task-definition mate-demo-dev-$service
done

# 6.2 Wait for services to stabilize
for service in django celery beat; do
  aws ecs wait services-stable \
    --cluster mate-dev \
    --services mate-demo-dev-$service
done
```

### Step 7: Test CI/CD Pipeline Integration

#### Test Dev Branch Deployment
```bash
# 7.1 Switch to dev branch
git checkout dev
git pull origin dev

# 7.2 Make a test change
echo "# Test deployment $(date)" >> README.md
git add README.md
git commit -m "test: Verify CI/CD deployment to dev environment"
git push origin dev

# 7.3 Monitor GitHub Actions
gh run list --workflow ci-cd.yml --branch dev --limit 1
gh run watch $(gh run list --workflow ci-cd.yml --branch dev --limit 1 --json databaseId -q '.[0].databaseId')
```

#### Test Staging Branch Deployment
```bash
# 7.4 Switch to staging branch
git checkout staging
git pull origin staging

# 7.5 Make a test change
echo "# Test staging deployment $(date)" >> README.md
git add README.md
git commit -m "test: Verify CI/CD deployment to staging environment"
git push origin staging

# 7.6 Monitor GitHub Actions
gh run list --workflow ci-cd.yml --branch staging --limit 1
gh run watch $(gh run list --workflow ci-cd.yml --branch staging --limit 1 --json databaseId -q '.[0].databaseId')
```

### Step 8: Verify Deployment Health
```bash
# 8.1 Check ECS service health
aws ecs describe-services \
  --cluster mate-dev \
  --services mate-demo-dev-django mate-demo-dev-celery mate-demo-dev-beat \
  --query 'services[].{name:serviceName,desired:desiredCount,running:runningCount,status:status}' \
  --output table

# 8.2 Check CloudWatch logs for errors
for service in django celery beat; do
  echo "Recent logs for $service:"
  aws logs tail /ecs/mate-dev/$service --since 5m
done

# 8.3 Test ALB endpoint (if configured)
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names mate-demo-dev-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text 2>/dev/null)

if [ ! -z "$ALB_DNS" ]; then
  curl -I http://$ALB_DNS/health/
fi

# 8.4 Check database connectivity
aws ecs run-task \
  --cluster mate-dev \
  --task-definition mate-demo-dev-django \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$(aws ec2 describe-subnets --filters "Name=tag:Environment,Values=dev" --query 'Subnets[?MapPublicIpOnLaunch==\`false\`].SubnetId' --output text | head -1)],securityGroups=[$(aws ec2 describe-security-groups --filters "Name=tag:Name,Values=mate-demo-dev-sg" --query 'SecurityGroups[0].GroupId' --output text)]}" \
  --overrides '{"containerOverrides":[{"name":"django","command":["python","manage.py","dbshell","-c","SELECT version();"]}]}'
```

## Success Criteria

✅ **Infrastructure Destruction**
- [ ] All demo tenant resources removed cleanly
- [ ] No orphaned resources in AWS
- [ ] Terraform state is clean

✅ **Infrastructure Recreation**
- [ ] RDS instance created and accessible
- [ ] ElastiCache cluster created and accessible
- [ ] ECS services created and running
- [ ] Task definitions match CI/CD expectations
- [ ] IAM roles and policies correctly configured
- [ ] Secrets Manager contains correct credentials

✅ **CI/CD Integration**
- [ ] Dev branch deploys to dev environment
- [ ] Staging branch deploys to dev environment (as configured)
- [ ] Docker images pushed to ECR successfully
- [ ] ECS services update with new images
- [ ] Database migrations run successfully
- [ ] All three services (django, celery, beat) deploy

✅ **Service Health**
- [ ] All ECS tasks are running
- [ ] No errors in CloudWatch logs
- [ ] ALB health checks passing (if configured)
- [ ] Database connectivity confirmed
- [ ] Redis connectivity confirmed

## Troubleshooting Guide

### Common Issues and Solutions

1. **Terraform Destroy Fails**
   ```bash
   # Force unlock if locked
   terraform force-unlock <LOCK_ID>
   
   # Remove resources manually if needed
   aws ecs delete-service --cluster mate-dev --service mate-demo-dev-django --force
   ```

2. **ECS Tasks Fail to Start**
   ```bash
   # Check task stopped reason
   aws ecs describe-tasks \
     --cluster mate-dev \
     --tasks $(aws ecs list-tasks --cluster mate-dev --service-name mate-demo-dev-django --query 'taskArns[0]' --output text) \
     --query 'tasks[0].stoppedReason'
   ```

3. **CI/CD Pipeline Fails**
   ```bash
   # Check GitHub Actions logs
   gh run view <RUN_ID> --log
   
   # Check AWS credentials
   aws sts get-caller-identity
   ```

4. **Database Connection Issues**
   ```bash
   # Verify security group rules
   aws ec2 describe-security-groups \
     --group-ids $(aws rds describe-db-instances --db-instance-identifier mate-demo-dev --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text) \
     --query 'SecurityGroups[0].IpPermissions'
   ```

## Notes

- The CI/CD pipeline uses git SHA for image tags, while Terraform might use 'latest'
- Environment naming is inconsistent (staging branch deploys to dev environment)
- Ensure AWS credentials have sufficient permissions for all operations
- The demo tenant is configured for minimal resources (t3.micro instances)

## Timeline

Estimated time for complete verification: **45-60 minutes**
- Pre-destruction verification: 5 minutes
- Destroy demo tenant: 10-15 minutes
- Recreate demo tenant: 10-15 minutes
- Docker build and push: 5-10 minutes
- CI/CD testing: 10 minutes
- Health verification: 5 minutes