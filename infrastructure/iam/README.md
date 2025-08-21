# IAM Policies for MATE Infrastructure

This directory contains IAM policies needed for deploying and managing the MATE infrastructure.

## Policies

### terraform-deploy-policy.json
**Purpose**: Full permissions for Terraform deployments (development/sandbox)
**Usage**: Attach to IAM user or role that runs Terraform

```bash
# Create policy
aws iam create-policy \
  --policy-name MATE-Terraform-Deploy \
  --policy-document file://terraform-deploy-policy.json

# Attach to user
aws iam attach-user-policy \
  --user-name your-terraform-user \
  --policy-arn arn:aws:iam::528424611228:policy/MATE-Terraform-Deploy
```

### terraform-deploy-policy-production.json
**Purpose**: Scoped permissions for production Terraform deployments
**Features**:
- Granular permissions per service
- Named statement IDs for auditing
- Production-ready security

```bash
# Create production policy
aws iam create-policy \
  --policy-name MATE-Terraform-Deploy-Production \
  --policy-document file://terraform-deploy-policy-production.json
```

## Required Permissions

The Terraform deployment needs permissions for:

| Service | Purpose |
|---------|---------|
| **EC2/VPC** | Create networking infrastructure |
| **ECS** | Container orchestration |
| **ECR** | Docker image repositories |
| **RDS** | PostgreSQL databases per tenant |
| **ElastiCache** | Redis instances per tenant |
| **S3** | Object storage and Terraform state |
| **EFS** | File storage for AI models |
| **IAM** | Create service roles |
| **KMS** | Encryption keys |
| **Cognito** | User authentication |
| **Route53** | DNS management |
| **ACM** | SSL certificates |
| **ALB** | Load balancers |
| **WAF** | Web application firewall |
| **CloudWatch** | Logging and monitoring |
| **Secrets Manager** | Database credentials |
| **DynamoDB** | Terraform state locking |
| **SNS** | Notifications |
| **SES** | Email sending |

## Security Best Practices

1. **Use Production Policy**: For production deployments, use the scoped policy
2. **MFA Required**: Enable MFA for any user with these permissions
3. **Audit Regularly**: Review CloudTrail logs for Terraform actions
4. **Rotate Credentials**: Rotate access keys regularly
5. **Use Roles**: Prefer IAM roles over long-lived access keys

## CI/CD Integration

For GitHub Actions or other CI/CD:

```yaml
# Use OIDC provider (recommended)
- uses: aws-actions/configure-aws-credentials@v1
  with:
    role-to-assume: arn:aws:iam::528424611228:role/MATE-Terraform-Deploy
    aws-region: us-east-1
```

## Troubleshooting

If Terraform fails with permission errors:

1. Check CloudTrail for the exact action that failed
2. Verify the policy is attached to your user/role
3. Ensure you're in the correct AWS account
4. Check for any SCPs (Service Control Policies) if using AWS Organizations