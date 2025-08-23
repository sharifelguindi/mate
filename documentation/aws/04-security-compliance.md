# Security & Compliance

## Implemented Security Features

### Encryption
- **At Rest**: KMS encryption for RDS, S3, EFS
- **In Transit**: TLS 1.2+ for all connections
- **Secrets**: AWS Secrets Manager for credentials

### Network Security
- VPC with private subnets for databases
- Security groups with least privilege
- WAF enabled on ALB
- No direct internet access for compute resources

### Access Control
- Cognito for user authentication
- IAM roles for service access
- MFA support

## HIPAA Compliance

### Prerequisites
1. Sign BAA with AWS
2. Use only HIPAA-eligible services
3. Enable audit logging

### Audit Configuration
```bash
# Enable CloudTrail
aws cloudtrail create-trail \
  --name mate-audit \
  --s3-bucket-name mate-audit-logs

# Enable VPC Flow Logs
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-xxx \
  --traffic-type ALL \
  --log-destination-type s3

# Set CloudWatch retention
aws logs put-retention-policy \
  --log-group-name /ecs/mate-demo-dev \
  --retention-in-days 2555  # 7 years
```

## Security Monitoring

```bash
# Check encryption status
aws rds describe-db-instances --query 'DBInstances[*].[DBInstanceIdentifier,StorageEncrypted]'
aws s3api get-bucket-encryption --bucket mate-demo-dev-data

# Review security groups
aws ec2 describe-security-groups --filters "Name=group-name,Values=mate-*"

# Audit IAM policies
aws iam get-account-authorization-details
```
