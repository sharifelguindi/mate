# Security & HIPAA Compliance Guide

## Overview

This guide covers security best practices and HIPAA compliance requirements for MATE deployed on AWS.

## HIPAA Compliance Checklist

### ✅ Administrative Safeguards

#### Business Associate Agreement (BAA)
- [ ] Sign BAA with AWS - [AWS HIPAA Compliance](https://aws.amazon.com/compliance/hipaa-compliance/)
- [ ] Ensure all third-party services have BAAs
- [ ] Document all data processing agreements

#### Access Controls
- [ ] Implement unique user identification (Cognito)
- [ ] Automatic logoff configured (session timeout)
- [ ] Encryption and decryption implemented

#### Audit Controls
- [ ] CloudTrail enabled for all regions
- [ ] CloudWatch Logs retention set to 7 years
- [ ] VPC Flow Logs enabled
- [ ] S3 access logging enabled

### ✅ Physical Safeguards

AWS handles physical security for their data centers. Ensure:
- [ ] Using only HIPAA-eligible AWS services
- [ ] Data residency requirements met (specific regions)

### ✅ Technical Safeguards

#### Encryption at Rest
```bash
# Verify RDS encryption
aws rds describe-db-instances \
  --query 'DBInstances[*].[DBInstanceIdentifier,StorageEncrypted]' \
  --output table

# Verify S3 encryption
aws s3api get-bucket-encryption --bucket <bucket-name>

# Verify EFS encryption
aws efs describe-file-systems \
  --query 'FileSystems[*].[FileSystemId,Encrypted]' \
  --output table
```

#### Encryption in Transit
- All data transmitted over TLS 1.2+
- ElastiCache with encryption enabled
- RDS with SSL enforcement

## Security Configuration

### IAM Best Practices

#### Least Privilege Access
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::mate-${tenant}/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    }
  ]
}
```

#### Enable MFA for All Users
```bash
# Enforce MFA in Cognito
aws cognito-idp update-user-pool \
  --user-pool-id <pool-id> \
  --mfa-configuration ON
```

### Network Security

#### Security Groups Configuration
```hcl
# Example: Database security group
resource "aws_security_group" "database" {
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]  # Only from app
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

#### WAF Rules
- SQL injection protection
- Cross-site scripting protection
- Rate limiting (2000 requests/5min)
- Geographic restrictions if needed

### Data Protection

#### Backup Strategy
```bash
# Automated RDS backups
aws rds modify-db-instance \
  --db-instance-identifier <instance-id> \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00"

# S3 versioning and lifecycle
aws s3api put-bucket-versioning \
  --bucket <bucket-name> \
  --versioning-configuration Status=Enabled
```

#### Key Management
```bash
# Rotate KMS keys annually
aws kms enable-key-rotation --key-id <key-id>

# Rotate secrets automatically
aws secretsmanager rotate-secret \
  --secret-id <secret-id> \
  --rotation-lambda-arn <lambda-arn>
```

## Audit Logging

### CloudTrail Configuration
```bash
# Create trail with validation
aws cloudtrail create-trail \
  --name mate-audit-trail \
  --s3-bucket-name mate-audit-logs \
  --enable-log-file-validation \
  --event-selectors '[
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": [
        {
          "Type": "AWS::S3::Object",
          "Values": ["arn:aws:s3:::mate-*/*"]
        },
        {
          "Type": "AWS::RDS::DBCluster",
          "Values": ["arn:aws:rds:*:*:cluster:mate-*"]
        }
      ]
    }
  ]'
```

### Log Analysis
```bash
# Query CloudWatch Insights for failed login attempts
aws logs start-query \
  --log-group-name /aws/cognito/userpools/<pool-id> \
  --start-time $(date -u -d '24 hours ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message
    | filter @message like /Authentication failed/
    | stats count() by bin(5m)
  '
```

## Incident Response

### Preparation
1. Document incident response procedures
2. Configure SNS alerts for security events
3. Regular security drills

### Detection
```bash
# Enable GuardDuty
aws guardduty create-detector --enable --finding-publishing-frequency ONE_HOUR

# Enable Security Hub
aws securityhub enable-security-hub --enable-default-standards
```

### Response Playbooks

#### Suspected Data Breach
1. Isolate affected resources
2. Preserve logs and snapshots
3. Notify compliance officer
4. Document timeline and actions

#### Suspicious Activity
```bash
# Block suspicious IP
aws wafv2 update-ip-set \
  --id <ip-set-id> \
  --addresses <suspicious-ip>/32

# Revoke user access
aws cognito-idp admin-disable-user \
  --user-pool-id <pool-id> \
  --username <username>
```

## Compliance Monitoring

### AWS Config Rules
```bash
# Enable required Config rules
aws configservice put-config-rule --config-rule '{
  "ConfigRuleName": "encrypted-volumes",
  "Source": {
    "Owner": "AWS",
    "SourceIdentifier": "ENCRYPTED_VOLUMES"
  }
}'
```

### Regular Audits
- [ ] Monthly access review
- [ ] Quarterly security assessment
- [ ] Annual penetration testing
- [ ] Continuous vulnerability scanning

## Security Tools

### Automated Scanning
```bash
# Run AWS Inspector
aws inspector2 enable --resource-types EC2 ECR

# Check for exposed credentials
git secrets --install
git secrets --register-aws
```

### Monitoring Dashboard
Create CloudWatch dashboard for security metrics:
- Failed authentication attempts
- Unauthorized API calls
- Network anomalies
- Resource modifications

## Training & Awareness

### Required Training
- HIPAA compliance training for all staff
- AWS security best practices
- Incident response procedures
- Social engineering awareness

### Documentation
Maintain up-to-date:
- Security policies
- Access control matrix
- Data flow diagrams
- Risk assessments

## Useful Resources

- [AWS HIPAA Compliance Workbook](https://d1.awsstatic.com/whitepapers/compliance/AWS_HIPAA_Compliance_Whitepaper.pdf)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [HHS Security Risk Assessment Tool](https://www.healthit.gov/topic/privacy-security-and-hipaa/security-risk-assessment-tool)
- [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/)
