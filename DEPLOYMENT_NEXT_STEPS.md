# Next Steps After Infrastructure Creation

## What Just Happened
✅ Created demo tenant infrastructure in AWS:
- RDS PostgreSQL database
- ElastiCache Redis cluster  
- ECS task definitions (bootstrap only)
- ALB and target groups
- Security groups and networking
- EFS file systems for storage
- S3 buckets for data and logs
- IAM roles and policies
- Secrets in Secrets Manager

## What's Missing
❌ No Docker images in ECR yet
❌ ECS services can't start without images
❌ Database hasn't been initialized/migrated

## Proper Deployment via CI/CD

### Step 1: Trigger CI/CD Pipeline
```bash
# Make a small change to trigger the pipeline
git checkout dev
git pull origin dev
echo "# Triggering CI/CD deployment - $(date)" >> deployment.log
git add deployment.log
git commit -m "chore: Trigger initial deployment to demo tenant"
git push origin dev
```

### Step 2: CI/CD Will Automatically:
1. Run tests
2. Build Docker image from `compose/production/django/Dockerfile`
3. Tag with git SHA
4. Push to ECR repositories:
   - `mate-django-dev`
   - `mate-celery-dev` (same image, different entrypoint)
   - `mate-beat-dev` (same image, different entrypoint)
5. Update ECS task definitions with new image
6. Run database migrations via ECS task
7. Deploy new services to ECS cluster

### Step 3: Monitor Deployment
```bash
# Watch GitHub Actions
gh run list --workflow ci-cd.yml --branch dev --limit 1
gh run watch <RUN_ID>

# Check ECS services
aws ecs describe-services \
  --cluster mate-dev \
  --services mate-demo-dev-django mate-demo-dev-celery mate-demo-dev-beat \
  --region us-east-1 \
  --query 'services[].{name:serviceName,desired:desiredCount,running:runningCount}'

# Check CloudWatch logs
aws logs tail /ecs/mate-demo-dev/django --follow --region us-east-1
```

## Why CI/CD Instead of Manual?

1. **Consistency**: Same process for all environments
2. **Traceability**: Git SHA in image tags
3. **Testing**: Runs tests before deployment
4. **Migrations**: Handles database setup properly
5. **Secrets**: Uses Secrets Manager properly
6. **Task Definitions**: Updates with correct environment variables

## Environment Variables Set by CI/CD

The pipeline sets these automatically:
- `DATABASE_URL` from Secrets Manager
- `REDIS_URL` from Secrets Manager  
- `SECRET_KEY` from Secrets Manager
- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `AWS_STORAGE_BUCKET_NAME=mate-demo-dev-data`
- `DJANGO_ALLOWED_HOSTS` including ALB DNS

## Troubleshooting

If services don't start after CI/CD:
1. Check task stopped reason:
   ```bash
   aws ecs describe-tasks \
     --cluster mate-dev \
     --tasks $(aws ecs list-tasks --cluster mate-dev --service-name mate-demo-dev-django --query 'taskArns[0]' --output text) \
     --query 'tasks[0].stoppedReason'
   ```

2. Check CloudWatch logs for errors
3. Verify secrets exist in Secrets Manager
4. Check security group rules
5. Verify ECR images were pushed

## Important Notes

- The bootstrap task definitions use `:latest` tag temporarily
- CI/CD will update them with proper git SHA tags
- Don't manually push images - let CI/CD handle it
- The first deployment may take longer due to image builds