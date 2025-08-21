# Bootstrap Task Definitions for ECS Services
# These are minimal task definitions created only for initial service creation.
# The CI/CD pipeline will update these with proper container images and configurations.
# Terraform will NOT manage these after initial creation due to lifecycle ignore_changes.

# Bootstrap task definition for Celery Worker
resource "aws_ecs_task_definition" "celery_bootstrap" {
  family                   = "${local.tenant_prefix}-celery"
  network_mode            = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                     = local.config.celery_cpu
  memory                  = local.config.celery_memory
  execution_role_arn      = aws_iam_role.ecs_task_execution.arn
  task_role_arn          = aws_iam_role.ecs_task.arn

  # Minimal container definition - will be replaced by CI/CD
  container_definitions = jsonencode([
    {
      name  = "celery"
      # Using a placeholder image - CI/CD will update this
      image = "${var.ecr_repositories["mate-django"]}:latest"
      command = ["/start-celeryworker"]

      essential = true
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.celery.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "celery"
        }
      }

      environment = [
        {
          name  = "DJANGO_SETTINGS_MODULE"
          value = "config.settings.production"
        }
      ]
    }
  ])

  # IMPORTANT: After creation, CI/CD owns this resource
  lifecycle {
    ignore_changes = all
  }

  tags = {
    Name      = "${local.tenant_prefix}-celery"
    Tenant    = var.tenant_name
    ManagedBy = "CI/CD"
    Note      = "Bootstrap only - managed by CI/CD pipeline"
  }
}

# Bootstrap task definition for Celery Beat
resource "aws_ecs_task_definition" "beat_bootstrap" {
  family                   = "${local.tenant_prefix}-beat"
  network_mode            = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                     = 256
  memory                  = 512
  execution_role_arn      = aws_iam_role.ecs_task_execution.arn
  task_role_arn          = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "beat"
      image = "${var.ecr_repositories["mate-django"]}:latest"
      command = ["/start-celerybeat"]

      essential = true
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.beat.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "beat"
        }
      }

      environment = [
        {
          name  = "DJANGO_SETTINGS_MODULE"
          value = "config.settings.production"
        }
      ]
    }
  ])

  lifecycle {
    ignore_changes = all
  }

  tags = {
    Name      = "${local.tenant_prefix}-beat"
    Tenant    = var.tenant_name
    ManagedBy = "CI/CD"
    Note      = "Bootstrap only - managed by CI/CD pipeline"
  }
}

# ECS Services reference the bootstrap task definitions
# CI/CD will update them with new revisions
resource "aws_ecs_service" "celery" {
  name            = "${local.tenant_prefix}-celery"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.celery_bootstrap.arn
  desired_count   = 1  # Will be managed by CI/CD autoscaling
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tenant.id]
    assign_public_ip = false
  }

  # Ignore task_definition changes as CI/CD manages deployments
  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_task_execution,
    aws_iam_role_policy.ecs_task_s3,
    aws_iam_role_policy.ecs_task_cloudwatch
  ]

  tags = {
    Name   = "${local.tenant_prefix}-celery"
    Tenant = var.tenant_name
  }
}

resource "aws_ecs_service" "beat" {
  name            = "${local.tenant_prefix}-beat"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.beat_bootstrap.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tenant.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_task_execution,
    aws_iam_role_policy.ecs_task_s3,
    aws_iam_role_policy.ecs_task_cloudwatch
  ]

  tags = {
    Name   = "${local.tenant_prefix}-beat"
    Tenant = var.tenant_name
  }
}

# CloudWatch Log Groups are defined in ecs.tf
