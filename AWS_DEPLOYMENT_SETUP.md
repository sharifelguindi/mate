# AWS Deployment Setup for MATE

## 🚨 Required GitHub Secrets

You need to configure these secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

### Core AWS Secrets (REQUIRED)
```
AWS_ACCOUNT_ID         # Your AWS account ID (e.g., 528424611228)
AWS_ACCESS_KEY_ID      # IAM user access key for deployments
AWS_SECRET_ACCESS_KEY  # IAM user secret key for deployments
```

### Optional Secrets
```
SLACK_WEBHOOK          # For deployment notifications (optional)
CODECOV_TOKEN          # For code coverage reports (optional)
```

## 📋 Prerequisites Checklist

### 1. AWS Account Setup
- [ ] AWS Account created and verified
- [ ] AWS CLI installed and configured locally
- [ ] Terraform installed (v1.5+)
- [ ] Docker installed for building images

### 2. AWS Resources to Create
The following will be created by Terraform, but you need to ensure:
- [ ] AWS region selected (default: us-east-1)
- [ ] Domain name ready (e.g., mate.yourdomain.com)
- [ ] SSL certificate will be auto-created via ACM

### 3. Git Branches (✅ Already Set Up)
- [x] main branch (production)
- [x] staging branch 
- [x] dev branch

## 🚀 Step-by-Step Setup Guide

### Step 1: Create IAM User for GitHub Actions

```bash
# Create deployment user
aws iam create-user --user-name github-actions-deploy

# Create and attach the policy (use the policy from infrastructure/iam/terraform-deploy-policy.json)
aws iam create-policy --policy-name GitHubActionsDeployPolicy \
  --policy-document file://infrastructure/iam/terraform-deploy-policy.json

# Attach policy to user
aws iam attach-user-policy \
  --user-name github-actions-deploy \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/GitHubActionsDeployPolicy

# Create access keys (SAVE THESE!)
aws iam create-access-key --user-name github-actions-deploy
```

### Step 2: Create Terraform Backend Resources

```bash
# Set your AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket mate-terraform-state-${AWS_ACCOUNT_ID} \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket mate-terraform-state-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name mate-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### Step 3: Configure GitHub Secrets

Using GitHub CLI:
```bash
# Set GitHub secrets
gh secret set AWS_ACCOUNT_ID --body "YOUR_ACCOUNT_ID"
gh secret set AWS_ACCESS_KEY_ID --body "YOUR_ACCESS_KEY"
gh secret set AWS_SECRET_ACCESS_KEY --body "YOUR_SECRET_KEY"
```

Or manually:
1. Go to https://github.com/sharifelguindi/mate/settings/secrets/actions
2. Click "New repository secret"
3. Add each secret with its value

### Step 4: Update Terraform Configuration

Edit `infrastructure/terraform/base/main.tf` to update the S3 backend:
```hcl
backend "s3" {
  bucket         = "mate-terraform-state-YOUR_ACCOUNT_ID"  # Update this
  key            = "infrastructure/terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "mate-terraform-locks"
}
```

Edit `infrastructure/terraform/base/terraform.tfvars`:
```hcl
environment         = "dev"
aws_region         = "us-east-1"
vpc_cidr           = "10.0.0.0/16"
domain_name        = "YOUR_DOMAIN.com"  # Update this
create_route53_zone = true  # Set to true if you want Terraform to create the zone
cognito_domain     = "YOUR_UNIQUE_COGNITO_DOMAIN"  # Must be globally unique
cost_center        = "engineering"
enable_deletion_protection = false  # Set to true for production
```

### Step 5: Deploy Base Infrastructure

```bash
cd infrastructure/terraform/base

# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Deploy base infrastructure
terraform apply

# Save outputs for reference
terraform output -json > outputs.json
```

### Step 6: Create ECR Repositories

The ECR repositories should be created by Terraform, but if needed manually:
```bash
# For each environment (dev, staging, production)
for env in dev staging production; do
  for service in django celery beat; do
    aws ecr create-repository --repository-name mate-${service}-${env}
  done
done
```

### Step 7: Deploy a Demo Tenant

```bash
cd infrastructure/terraform/tenants/demo

# Update terraform.tfvars with your configuration
terraform init
terraform plan
terraform apply
```

### Step 8: Initial Docker Image Build & Push

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Build and push initial images
docker build -f compose/production/django/Dockerfile -t mate-django:latest .

# Tag and push for each service
for service in django celery beat; do
  docker tag mate-django:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/mate-${service}-dev:latest
  docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/mate-${service}-dev:latest
done
```

### Step 9: Configure GitHub Environments

```bash
# Create environments
for env in development staging production; do
  gh api -X PUT /repos/sharifelguindi/mate/environments/$env
done

# Add protection rules for production
gh api -X PUT /repos/sharifelguindi/mate/environments/production \
  --field wait_timer=10 \
  --field deployment_branch_policy='{"protected_branches":true,"custom_branch_policies":false}'
```

### Step 10: Test the CI/CD Pipeline

```bash
# Make a test commit to dev branch
git checkout dev
echo "# Test deployment" >> README.md
git add README.md
git commit -m "Test: CI/CD pipeline deployment"
git push origin dev
```

Then check: https://github.com/sharifelguindi/mate/actions

## 🔍 Verification Checklist

After setup, verify:

- [ ] GitHub Actions can authenticate to AWS
- [ ] Terraform state is stored in S3
- [ ] ECR repositories are created
- [ ] ECS cluster is running
- [ ] VPC and networking are configured
- [ ] RDS and ElastiCache are provisioned (if tenant deployed)
- [ ] Application Load Balancer is healthy
- [ ] Route53 DNS is configured
- [ ] SSL certificate is validated

## 🛠️ Troubleshooting

### Common Issues

1. **GitHub Actions fails with AWS credentials error**
   - Verify secrets are set correctly in GitHub
   - Check IAM user has correct permissions

2. **Terraform state lock error**
   - Someone else might be running Terraform
   - Check DynamoDB table exists
   - Force unlock if needed: `terraform force-unlock LOCK_ID`

3. **ECR push fails**
   - Ensure ECR repositories exist
   - Check Docker is logged into ECR
   - Verify IAM permissions include ECR access

4. **ECS tasks fail to start**
   - Check CloudWatch logs
   - Verify task definition has correct image
   - Check security groups and networking
   - Ensure secrets are configured in Secrets Manager

5. **Database connection errors**
   - Verify RDS is running
   - Check security group allows connection from ECS
   - Verify database credentials in Secrets Manager

## 📝 Environment-Specific Configuration

### Development (dev branch)
- Auto-deploys on push
- Uses minimal resources
- No approval required
- Domain: dev.mate.yourdomain.com

### Staging (staging branch)
- Auto-deploys on push
- Production-like environment
- No approval required
- Domain: staging.mate.yourdomain.com

### Production (main branch)
- Requires manual trigger
- Requires approval
- Blue-green deployment
- Full backups before deployment
- Domain: mate.yourdomain.com

## 🔐 Security Notes

1. **Never commit secrets to git**
2. **Use IAM roles whenever possible**
3. **Enable MFA on AWS root account**
4. **Rotate access keys regularly**
5. **Use least privilege principle for IAM policies**
6. **Enable CloudTrail for audit logging**
7. **Use AWS Secrets Manager for application secrets**

## 📊 Cost Optimization

Estimated monthly costs:
- Dev environment: ~$50-100
- Staging environment: ~$100-150
- Production (per tenant): ~$150-300

Cost saving tips:
- Use Fargate Spot for dev/staging
- Schedule dev/staging to shut down at night
- Use Reserved Instances for production RDS
- Enable S3 lifecycle policies
- Monitor with AWS Cost Explorer

## 🚦 Next Steps

Once everything is set up:

1. **Deploy your first tenant**: 
   ```bash
   ./scripts/provision-tenant.sh
   ```

2. **Monitor deployments**:
   - GitHub Actions: https://github.com/sharifelguindi/mate/actions
   - AWS Console: https://console.aws.amazon.com/ecs
   - CloudWatch: https://console.aws.amazon.com/cloudwatch

3. **Set up monitoring**:
   - Configure CloudWatch alarms
   - Set up SNS notifications
   - Enable Container Insights

4. **Configure backups**:
   - Enable automated RDS backups
   - Set up S3 cross-region replication
   - Test disaster recovery procedures

## 📚 Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

## ⚡ Quick Commands Reference

```bash
# Check AWS credentials
aws sts get-caller-identity

# View Terraform state
terraform state list

# Force deployment from GitHub
gh workflow run ci-cd.yml --ref dev

# Check ECS service status
aws ecs describe-services --cluster mate-dev --services mate-demo-dev-django

# View CloudWatch logs
aws logs tail /ecs/mate-dev/django --follow

# Scale ECS service
aws ecs update-service --cluster mate-dev --service mate-demo-dev-django --desired-count 3
```

---
Last Updated: 2025-08-21