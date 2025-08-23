# Deployment Guide

## CI/CD Pipeline

GitHub Actions automatically deploys on push to:
- `dev` → Development environment
- `staging` → Staging environment
- `main` → Production environment

### Manual Deployment

```bash
# Build and push Docker images
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 528424611228.dkr.ecr.us-east-1.amazonaws.com

docker build -f compose/production/django/Dockerfile -t mate-django .
docker tag mate-django:latest 528424611228.dkr.ecr.us-east-1.amazonaws.com/mate-django-dev:latest
docker push 528424611228.dkr.ecr.us-east-1.amazonaws.com/mate-django-dev:latest

# Force ECS deployment
aws ecs update-service --cluster mate-dev --service mate-demo-dev-django --force-new-deployment
```

## Database Operations

```bash
# Run migrations
aws ecs run-task --cluster mate-dev \
  --task-definition mate-demo-dev-django \
  --overrides '{"containerOverrides":[{"name":"django","command":["python","manage.py","migrate"]}]}'

# Create superuser
aws ecs run-task --cluster mate-dev \
  --task-definition mate-demo-dev-django \
  --overrides '{"containerOverrides":[{"name":"django","command":["python","manage.py","createsuperuser"]}]}'
```

## Monitoring

```bash
# View service status
aws ecs describe-services --cluster mate-dev --services mate-demo-dev-django

# Check logs
aws logs tail /ecs/mate-demo-dev/django --follow

# View metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=mate-demo-dev-django \
  --start-time $(date -u -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Average
```
