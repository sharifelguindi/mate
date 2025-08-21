# GitHub Actions CI/CD Documentation

## Overview

This repository uses GitHub Actions for automated CI/CD pipelines to build, test, and deploy the MATE application to AWS ECS.

## Workflows

### 1. CI/CD Pipeline (`ci-cd.yml`)
**Triggers:** Push to main/dev/staging branches, Pull requests, Manual dispatch

**Jobs:**
- **Test**: Runs unit tests, integration tests, and code quality checks
- **Build**: Builds and pushes Docker images to Amazon ECR
- **Migrate**: Runs database migrations using ECS tasks
- **Deploy**: Deploys services to ECS using rolling updates
- **Smoke Test**: Validates deployment with health checks

### 2. Production Deployment (`production-deploy.yml`)
**Triggers:** Manual dispatch only (requires approval)

**Features:**
- Manual approval gate via GitHub Environments
- Pre-deployment validation and backups
- Blue-green deployment strategy
- Automatic rollback on failure
- Post-deployment validation
- Audit logging to DynamoDB

### 3. Security Scanning (`security.yml`)
**Triggers:** Daily schedule, Push to main/dev/staging, Manual dispatch

**Scans:**
- Container vulnerability scanning (Trivy)
- Dependency security scanning (Safety, pip-audit)
- Static application security testing (Bandit, Semgrep)
- Infrastructure security scanning (Checkov, tfsec)
- Secrets scanning (Gitleaks, TruffleHog)
- License compliance checking

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings:

### AWS Credentials
- `AWS_ACCOUNT_ID`: Your AWS account ID
- `AWS_ACCESS_KEY_ID`: AWS IAM access key
- `AWS_SECRET_ACCESS_KEY`: AWS IAM secret key

### Notifications
- `SLACK_WEBHOOK`: Slack webhook URL for deployment notifications

### Environments
Configure GitHub Environments for:
- `development`
- `staging`
- `production` (with required reviewers)

## Deployment Process

### Development/Staging Deployment
1. Push code to `dev` or `staging` branch
2. Tests run automatically
3. Docker images build and push to ECR
4. Database migrations execute
5. ECS services update with new images
6. Smoke tests validate deployment

### Production Deployment
1. Trigger manual workflow from Actions tab
2. Select tenant and version
3. Approve deployment (required reviewers)
4. Pre-deployment validation runs
5. Database backup created
6. Blue-green deployment executes
7. Health checks validate
8. Notification sent to Slack

### Rollback Process
1. Trigger production deployment workflow
2. Enable "rollback" option
3. Select tenant to rollback
4. Previous version automatically restored

## Local Development

### Building Docker Images
```bash
# Build web service
docker build -f compose/production/django/Dockerfile \
  --target web \
  -t mate-web:local .

# Build celery worker
docker build -f compose/production/django/Dockerfile \
  --target celery \
  -t mate-celery:local .

# Build celery beat
docker build -f compose/production/django/Dockerfile \
  --target beat \
  -t mate-beat:local .
```

### Testing Locally
```bash
# Run tests
docker-compose -f docker-compose.test.yml run --rm django pytest

# Run security scans
docker run --rm -v $(pwd):/src \
  aquasec/trivy fs /src

# Run linting
docker-compose -f docker-compose.local.yml run --rm django \
  flake8 mate/
```

## Monitoring

### CloudWatch Metrics
Monitor these metrics in CloudWatch:
- ECS Service CPU/Memory utilization
- ALB Target Health
- RDS CPU/Storage/Connections
- ElastiCache CPU/Memory/Evictions

### Application Logs
View logs in CloudWatch Log Groups:
- `/ecs/mate-{environment}/django`
- `/ecs/mate-{environment}/celery`
- `/ecs/mate-{environment}/beat`

### Deployment History
Track deployments in:
- GitHub Actions history
- DynamoDB `mate-deployments` table
- CloudWatch Events

## Troubleshooting

### Failed Deployment
1. Check GitHub Actions logs
2. Review CloudWatch logs for the service
3. Verify ECS service events in AWS Console
4. Check target health in ALB target groups

### Database Migration Issues
1. Check migration task logs in CloudWatch
2. Verify database connectivity
3. Review migration files for errors
4. Manually run migrations if needed:
   ```bash
   aws ecs run-task \
     --cluster mate-{environment} \
     --task-definition mate-demo-{environment}-django \
     --launch-type FARGATE \
     --overrides '{"containerOverrides":[{"name":"django","command":["python","manage.py","migrate"]}]}'
   ```

### Container Health Check Failures
1. Check application logs
2. Verify environment variables
3. Test database connectivity
4. Review security group rules

## Best Practices

1. **Always test in staging first** before production deployment
2. **Use semantic versioning** for releases
3. **Monitor metrics** after deployment
4. **Keep secrets rotated** regularly
5. **Review security scan results** before merging
6. **Document breaking changes** in pull requests
7. **Use feature flags** for gradual rollouts

## Support

For issues or questions:
1. Check this documentation
2. Review GitHub Actions logs
3. Contact the DevOps team
4. Create an issue in the repository