# MATE - AWS Setup Guide

A HIPAA-compliant, multi-tenant healthcare platform built on AWS ECS with complete infrastructure isolation per hospital/clinic.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [AWS Account Setup](#aws-account-setup)
- [Initial AWS Configuration](#initial-aws-configuration)
- [Infrastructure Deployment](#infrastructure-deployment)
- [Application Deployment](#application-deployment)
- [Tenant Provisioning](#tenant-provisioning)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Security & Compliance](#security--compliance)
- [Cost Management](#cost-management)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

1. **AWS CLI v2** - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

2. **Terraform v1.5+** - [Installation Guide](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
```bash
# macOS
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Linux
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Verify installation
terraform --version
```

3. **Docker** - [Installation Guide](https://docs.docker.com/get-docker/)
```bash
# macOS
brew install --cask docker

# Linux (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Verify installation
docker --version
```

4. **Additional Tools**
```bash
# jq for JSON processing
brew install jq  # macOS
sudo apt-get install jq  # Linux

# Session Manager Plugin (for ECS debugging)
# https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html
```

## AWS Account Setup

### 1. Create AWS Account

1. Visit [AWS Sign Up](https://portal.aws.amazon.com/billing/signup)
2. Follow the [detailed account creation guide](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-creating.html)
3. Set up [MFA for root account](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html#id_root-user_manage_mfa)
4. Run aws configure on root to create deployment role, then remove.
```bash
# Configure root user first to create iam roles/policy, then reconfigure role and remove root access
aws configure
```

### 2. Create IAM User for Deployment

Following [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html):

```bash
# Create IAM user
aws iam create-user --user-name mate-deploy

# Create the deployment policy with all required permissions
aws iam create-policy --policy-name MATEDeploymentPolicy --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:*",
        "ecr:*",
        "rds:*",
        "elasticache:*",
        "s3:*",
        "iam:*",
        "logs:*",
        "secretsmanager:*",
        "kms:*",
        "cognito-idp:*",
        "route53:*",
        "acm:*",
        "elasticloadbalancing:*",
        "autoscaling:*",
        "cloudwatch:*",
        "sns:*",
        "ses:*",
        "wafv2:*",
        "ec2:*",
        "elasticfilesystem:*",
        "application-autoscaling:*",
        "dynamodb:*"
      ],
      "Resource": "*"
    }
  ]
}'

# Get your AWS account ID (you'll need this for the next command)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach the policy to the user
aws iam attach-user-policy --user-name mate-deploy --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/MATEDeploymentPolicy

# Create access keys (SAVE THESE SECURELY!)
aws iam create-access-key --user-name mate-deploy
```

### 3. Configure AWS CLI

[AWS CLI Configuration Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)

```bash
aws configure --profile mate-deploy
# AWS Access Key ID [None]: YOUR_ACCESS_KEY
# AWS Secret Access Key [None]: YOUR_SECRET_KEY
# Default region name [None]: us-east-1
# Default output format [None]: json

# Set as default profile
export AWS_PROFILE=mate-deploy
```

### 4. Enable Required AWS Services

Enable these services in your AWS account:

1. **Amazon ECS** - [Getting Started](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/get-set-up-for-amazon-ecs.html)
2. **Amazon RDS** - [Setting Up](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_SettingUp.html)
3. **Amazon ElastiCache** - [Getting Started](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/GettingStarted.html)
4. **Amazon Cognito** - [Getting Started](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-getting-started.html)
5. **Amazon SES** - [Setting Up](https://docs.aws.amazon.com/ses/latest/dg/setting-up.html)

## Initial AWS Configuration

### 1. Set Up Terraform Backend

[Terraform S3 Backend Documentation](https://developer.hashicorp.com/terraform/language/settings/backends/s3)

```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket mate-terraform-state-$(aws sts get-caller-identity --query Account --output text) \
  --region us-east-1

# Enable versioning for state protection
aws s3api put-bucket-versioning \
  --bucket mate-terraform-state-$(aws sts get-caller-identity --query Account --output text) \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket mate-terraform-state-$(aws sts get-caller-identity --query Account --output text) \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        },
        "BucketKeyEnabled": true
      }
    ]
  }'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name mate-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --tags Key=Project,Value=MATE Key=Environment,Value=production
```

### 2. Configure DNS for Your Domain

You have two options depending on where your domain is registered:

#### Option A: Using a Subdomain (Recommended for Testing)
If using a subdomain like `mate.yourdomain.com` with an existing domain:

1. **Create Route53 Hosted Zone**:
```bash
# Create hosted zone for your subdomain
aws route53 create-hosted-zone \
  --name mate.yourdomain.com \
  --caller-reference $(date +%s) \
  --hosted-zone-config Comment="MATE"

# Get the nameservers (save these for the next step!)
aws route53 list-hosted-zones --query "HostedZones[?Name=='mate.yourdomain.com.'].Id" --output text | xargs aws route53 get-hosted-zone --id | jq -r '.DelegationSet.NameServers[]'
```

2. **Update Your Domain Registrar** (GoDaddy, Namecheap, etc.):
   - Log into your domain registrar's DNS management
   - Add NS records for your subdomain:
     ```
     Host: mate
     Type: NS  
     TTL: 3600
     Value: [Add each of the 4 nameservers from Route53 as separate records]
     ```
   - **Important**: This delegates ONLY the subdomain to AWS, leaving your root domain (email, etc.) untouched

3. **Verify DNS Delegation** (wait 5-10 minutes after updating):
```bash
# Check if delegation is working
dig mate.yourdomain.com NS

# You should see the Route53 nameservers in the response
```

#### Option B: Direct CNAME/A Record (Simple Sandbox)
For a single-tenant test without Route53:
- After deploying, get your ALB DNS name from Terraform output
- In your registrar, create: `mate.yourdomain.com CNAME → your-alb-dns.amazonaws.com`
- Note: This option requires manual SSL certificate management

#### Option C: Using Root Domain (Not Recommended for Testing)
Only if you want to dedicate the entire domain to MATE:
```bash
# Create hosted zone for root domain
aws route53 create-hosted-zone \
  --name yourdomain.com \
  --caller-reference $(date +%s) \
  --hosted-zone-config Comment="MATE"
```
Then update ALL nameservers at your registrar (this will affect email and all existing services)

### 3. Request SES Production Access

[Moving out of SES Sandbox](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)

1. Go to [SES Console](https://console.aws.amazon.com/ses/)
2. Request production access
3. Verify your domain:

```bash
# Verify domain for sending
aws ses verify-domain-identity --domain mate.yourdomain.com

# Get verification records
aws ses get-domain-verification-records --domain mate.yourdomain.com
```

### 4. Set Up AWS Organizations (Optional but Recommended)

[AWS Organizations Best Practices](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices.html)

For better tenant isolation, consider using AWS Organizations:

```bash
# Create organization
aws organizations create-organization --feature-set ALL

# Create OUs for different environments
aws organizations create-organizational-unit \
  --parent-id r-xxxx \
  --name Production

aws organizations create-organizational-unit \
  --parent-id r-xxxx \
  --name Staging
```

## Infrastructure Deployment

### 1. Clone and Configure Repository

```bash
git clone https://github.com/your-org/mate.git
cd mate

# Copy and configure Terraform variables
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
# terraform.tfvars
aws_region                 = "us-east-1"
environment               = "production"
domain_name               = "mate.yourdomain.com"
cognito_domain            = "mate-auth"
create_route53_zone       = false  # Set to true if you need Terraform to create the zone
enable_deletion_protection = true   # Protect RDS/ElastiCache from accidental deletion

# VPC Configuration
vpc_cidr = "10.0.0.0/16"

# Cost allocation
cost_center = "engineering"
```

### 2. Deploy Base Infrastructure

[Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan -out=tfplan

# Deploy base infrastructure (VPC, ECS Cluster, ECR, Cognito)
terraform apply tfplan

# Save important outputs
terraform output -json > outputs.json
```

This creates:
- **VPC** with public/private subnets across 3 AZs
- **ECS Cluster** for container orchestration
- **ECR Repositories** for Docker images
- **Cognito User Pool** for authentication
- **KMS Keys** for encryption
- **Base IAM Roles** and policies

### 3. Build and Push Docker Images

[ECR Documentation](https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html)

```bash
# Get ECR login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(terraform output -raw ecr_registry)

# Build images
docker build -f compose/production/django/Dockerfile \
  --build-arg BUILD_ENVIRONMENT=production \
  -t $(terraform output -raw ecr_registry)/mate-web:latest \
  -t $(terraform output -raw ecr_registry)/mate-web:$(git rev-parse --short HEAD) .

# Push images
docker push $(terraform output -raw ecr_registry)/mate-web:latest
docker push $(terraform output -raw ecr_registry)/mate-web:$(git rev-parse --short HEAD)

# Tag for Celery and Beat (same image, different entrypoints)
docker tag $(terraform output -raw ecr_registry)/mate-web:latest $(terraform output -raw ecr_registry)/mate-celery:latest
docker tag $(terraform output -raw ecr_registry)/mate-web:latest $(terraform output -raw ecr_registry)/mate-beat:latest

docker push $(terraform output -raw ecr_registry)/mate-celery:latest
docker push $(terraform output -raw ecr_registry)/mate-beat:latest
```

## Application Deployment

### 1. Deploy Your First Tenant

Create tenant configuration:
```bash
# Create tenant configuration file
cat > infrastructure/terraform/tenants/hospital-demo.tfvars <<EOF
tenants = {
  "hospital-demo" = {
    display_name = "Demo Hospital"
    subdomain    = "demo"
    tier         = "standard"
    
    # RDS Configuration
    rds_instance_class      = "db.t4g.medium"
    rds_allocated_storage   = 20
    rds_max_storage        = 100
    rds_backup_retention   = 7
    rds_multi_az           = false
    
    # ElastiCache Configuration  
    redis_node_type       = "cache.t4g.micro"
    redis_num_cache_nodes = 1
    
    # ECS Service Configuration
    django_desired_count  = 2
    django_cpu           = 512
    django_memory        = 1024
    
    celery_desired_count = 1
    celery_cpu          = 256
    celery_memory       = 512
    
    # Auto-scaling
    enable_autoscaling     = true
    min_capacity          = 1
    max_capacity          = 4
    target_cpu_utilization = 70
    
    # Storage
    s3_versioning        = true
    s3_lifecycle_rules   = false
    efs_throughput_mode  = "bursting"
    
    # HIPAA Compliance
    hipaa_compliant      = true
    enable_audit_logging = true
    enable_flow_logs     = false
    data_retention_days  = 2555
    
    # Contact Information
    technical_contact = "admin@demo.com"
    billing_contact   = "billing@demo.com"
    
    # Cost allocation tags
    cost_center = "demo"
    department  = "engineering"
  }
}
EOF

# Deploy the tenant infrastructure
terraform plan -var-file="tenants/hospital-demo.tfvars"
terraform apply -var-file="tenants/hospital-demo.tfvars"
```

### 2. Initialize Database

[ECS Exec Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html)

```bash
# Run database migrations
aws ecs run-task \
  --cluster mate-production \
  --task-definition mate-hospital-demo-production-django \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$(terraform output -json private_subnet_ids | jq -r '.[]' | tr '\n' ',' | sed 's/,$//')]}" \
  --overrides '{
    "containerOverrides": [{
      "name": "django",
      "command": ["python", "manage.py", "migrate", "--noinput"]
    }]
  }'

# Create superuser
aws ecs run-task \
  --cluster mate-production \
  --task-definition mate-hospital-demo-production-django \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$(terraform output -json private_subnet_ids | jq -r '.[]' | tr '\n' ',' | sed 's/,$//')]}" \
  --overrides '{
    "containerOverrides": [{
      "name": "django",
      "command": ["python", "manage.py", "createsuperuser", "--email", "admin@demo.com", "--noinput"]
    }]
  }'

# Collect static files
aws ecs run-task \
  --cluster mate-production \
  --task-definition mate-hospital-demo-production-django \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$(terraform output -json private_subnet_ids | jq -r '.[]' | tr '\n' ',' | sed 's/,$//')]}" \
  --overrides '{
    "containerOverrides": [{
      "name": "django",
      "command": ["python", "manage.py", "collectstatic", "--noinput"]
    }]
  }'
```

### 3. Verify Deployment

```bash
# Check ECS services
aws ecs describe-services \
  --cluster mate-production \
  --services mate-hospital-demo-production-django \
  --query 'services[0].deployments'

# Check ALB health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names mate-hospital-demo-production-django \
    --query 'TargetGroups[0].TargetGroupArn' --output text)

# Get application URL
echo "Application URL: https://demo.mate.yourdomain.com"
```

## Tenant Provisioning

### Automated Provisioning Script

```bash
# Make scripts executable
chmod +x scripts/provision-tenant.sh
chmod +x scripts/deploy.sh

# Run the provisioning script
./scripts/provision-tenant.sh

# Follow the interactive prompts:
# - Tenant name: hospital-a
# - Display name: Hospital A Medical Center  
# - Tier: enterprise
# - Contact email: admin@hospitala.com
# - Configure SSO: saml
```

### Manual Provisioning Steps

1. **Create Tenant in Database**:
```python
# Django shell command
python manage.py shell
from mate.tenants.models import Tenant

tenant = Tenant.objects.create(
    name="Hospital A Medical Center",
    slug="hospital-a",
    subdomain="hospital-a",
    deployment_status="provisioning",
    aws_region="us-east-1",
    plan="enterprise",
    hipaa_compliant=True,
)
```

2. **Configure Cognito SSO** (Optional):

[Cognito SAML Integration](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-saml-idp.html)

```bash
# Add SAML identity provider
aws cognito-idp create-identity-provider \
  --user-pool-id $(terraform output -raw cognito_user_pool_id) \
  --provider-name HospitalA_SAML \
  --provider-type SAML \
  --provider-details file://saml-metadata.json \
  --attribute-mapping email=email,name=name

# Create app client for the tenant
aws cognito-idp create-user-pool-client \
  --user-pool-id $(terraform output -raw cognito_user_pool_id) \
  --client-name hospital-a \
  --supported-identity-providers HospitalA_SAML COGNITO
```

## Monitoring & Maintenance

### CloudWatch Dashboards

[CloudWatch Dashboard Creation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/create_dashboard.html)

```bash
# Create custom dashboard
aws cloudwatch put-dashboard \
  --dashboard-name MATE-Overview \
  --dashboard-body file://cloudwatch-dashboard.json
```

### Set Up Alarms

[CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)

```bash
# High CPU alarm for ECS service
aws cloudwatch put-metric-alarm \
  --alarm-name mate-hospital-demo-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# RDS storage alarm
aws cloudwatch put-metric-alarm \
  --alarm-name mate-hospital-demo-rds-storage \
  --alarm-description "Alert when RDS storage exceeds 80%" \
  --metric-name FreeStorageSpace \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 20 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1
```

### Log Analysis

[CloudWatch Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)

```bash
# Query application logs
aws logs start-query \
  --log-group-name /ecs/mate-hospital-demo-production/django \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 100'
```

## Security & Compliance

### HIPAA Compliance Checklist

Following [AWS HIPAA Compliance Guide](https://docs.aws.amazon.com/whitepapers/latest/architecting-hipaa-security-and-compliance-on-aws/architecting-hipaa-security-and-compliance-on-aws.html):

1. **Sign BAA with AWS**: [AWS BAA](https://aws.amazon.com/compliance/hipaa-compliance/)

2. **Enable Encryption**:
```bash
# Verify RDS encryption
aws rds describe-db-instances \
  --db-instance-identifier mate-hospital-demo-production-db \
  --query 'DBInstances[0].StorageEncrypted'

# Verify S3 encryption
aws s3api get-bucket-encryption \
  --bucket mate-hospital-demo-production-data
```

3. **Enable Audit Logging**:
```bash
# Enable CloudTrail
aws cloudtrail create-trail \
  --name mate-audit-trail \
  --s3-bucket-name mate-audit-logs \
  --is-multi-region-trail \
  --enable-log-file-validation

# Enable VPC Flow Logs
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $(terraform output -raw vpc_id) \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flowlogs
```

### Security Best Practices

[AWS Security Best Practices](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/welcome.html)

1. **Enable GuardDuty**:
```bash
aws guardduty create-detector --enable
```

2. **Enable Security Hub**:
```bash
aws securityhub enable-security-hub
```

3. **Configure AWS WAF**:
[AWS WAF Documentation](https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html)
```bash
# Already configured in Terraform, verify:
terraform output waf_web_acl_id
```

4. **Implement Secrets Rotation**:
[Secrets Manager Rotation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)
```bash
aws secretsmanager rotate-secret \
  --secret-id mate-hospital-demo-production-django-secrets \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:xxxx:function:SecretsManagerRotation
```

## Cost Management

### Set Up Cost Alerts

[AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-create.html)

```bash
# Create monthly budget
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

Create `budget.json`:
```json
{
  "BudgetName": "MATE-Monthly-Budget",
  "BudgetLimit": {
    "Amount": "1000",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

### Cost Optimization

[AWS Cost Optimization](https://aws.amazon.com/architecture/cost-optimization/)

1. **Use Savings Plans**:
```bash
# View recommendations
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT
```

2. **Enable Auto-shutdown for Non-Production**:
```bash
# Create Lambda function to stop services at night
# See: https://aws.amazon.com/premiumsupport/knowledge-center/start-stop-lambda-eventbridge/
```

## Troubleshooting

### Common Issues and Solutions

1. **ECS Task Fails to Start**

[ECS Troubleshooting Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/troubleshooting.html)

```bash
# Check task stopped reason
aws ecs describe-tasks \
  --cluster mate-production \
  --tasks arn:aws:ecs:us-east-1:xxxx:task/xxxx \
  --query 'tasks[0].stoppedReason'

# Check container logs
aws logs get-log-events \
  --log-group-name /ecs/mate-hospital-demo-production/django \
  --log-stream-name ecs/django/task-id
```

2. **Database Connection Issues**

```bash
# Test connectivity from ECS task
aws ecs run-task \
  --cluster mate-production \
  --task-definition mate-hospital-demo-production-django \
  --launch-type FARGATE \
  --enable-execute-command \
  --overrides '{
    "containerOverrides": [{
      "name": "django",
      "command": ["nc", "-zv", "database-endpoint", "5432"]
    }]
  }'
```

3. **High Memory Usage**

[ECS Memory Management](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/capacity-tasksize.html)

```bash
# Check current memory usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name MemoryUtilization \
  --dimensions Name=ServiceName,Value=mate-hospital-demo-production-django \
  --start-time $(date -u -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Average
```

### Debugging with ECS Exec

[ECS Exec Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html)

```bash
# Enable ECS Exec on service
aws ecs update-service \
  --cluster mate-production \
  --service mate-hospital-demo-production-django \
  --enable-execute-command

# Connect to running container
aws ecs execute-command \
  --cluster mate-production \
  --task $(aws ecs list-tasks --cluster mate-production --service-name mate-hospital-demo-production-django --query 'taskArns[0]' --output text) \
  --container django \
  --interactive \
  --command "/bin/bash"
```

## Additional Resources

### AWS Documentation
- [ECS Best Practices Guide](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/intro.html)
- [RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
- [HIPAA on AWS](https://aws.amazon.com/compliance/hipaa-compliance/)

### Terraform Resources
- [Terraform AWS Modules](https://registry.terraform.io/namespaces/terraform-aws-modules)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)

### Monitoring and Observability
- [AWS Observability Best Practices](https://aws-observability.github.io/observability-best-practices/)
- [Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html)

### Cost Management
- [AWS Pricing Calculator](https://calculator.aws/#/)
- [Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
- [Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)

## Support

### Getting Help

1. **AWS Support**: [AWS Support Center](https://console.aws.amazon.com/support/)
2. **Community**: [AWS Forums](https://forums.aws.amazon.com/)
3. **Stack Overflow**: [AWS Tags](https://stackoverflow.com/questions/tagged/amazon-web-services)
4. **GitHub Issues**: Create issues in this repository

### Professional Services

For production deployments, consider:
- [AWS Professional Services](https://aws.amazon.com/professional-services/)
- [AWS Partner Network](https://aws.amazon.com/partners/)
- [AWS Managed Services](https://aws.amazon.com/managed-services/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.
