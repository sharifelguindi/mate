# Tenant-specific infrastructure module
# Each tenant gets isolated AWS resources

locals {
  tenant_prefix = "mate-${var.tenant_name}-${var.environment}"

  # Default configurations based on tier
  tier_defaults = {
    trial = {
      rds_instance_class    = "db.t4g.micro"
      redis_node_type       = "cache.t4g.micro"
      django_cpu           = 256
      django_memory        = 512
      celery_cpu          = 256
      celery_memory       = 512
      beat_cpu            = 256
      beat_memory         = 512
    }
    standard = {
      rds_instance_class    = "db.t4g.medium"
      redis_node_type       = "cache.t4g.small"
      django_cpu           = 512
      django_memory        = 1024
      celery_cpu          = 512
      celery_memory       = 1024
      beat_cpu            = 256
      beat_memory         = 512
    }
    enterprise = {
      rds_instance_class    = "db.r6g.xlarge"
      redis_node_type       = "cache.r7g.large"
      django_cpu           = 1024
      django_memory        = 2048
      celery_cpu          = 1024
      celery_memory       = 2048
      beat_cpu            = 512
      beat_memory         = 1024
    }
  }

  # Merge tier defaults with tenant config
  config = merge(
    local.tier_defaults[var.tenant_config.tier],
    var.tenant_config
  )
}

# Security group for tenant services
resource "aws_security_group" "tenant" {
  name        = "${local.tenant_prefix}-sg"
  description = "Security group for ${var.tenant_name} services"
  vpc_id      = var.vpc_id

  # Allow inbound traffic from ALB
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "Allow traffic from ALB"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name   = "${local.tenant_prefix}-sg"
    Tenant = var.tenant_name
  }
}

# Application Load Balancer for tenant
resource "aws_lb" "tenant" {
  name               = "${local.tenant_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = var.public_subnet_ids

  enable_deletion_protection = var.environment == "production"
  enable_http2              = true
  enable_cross_zone_load_balancing = true

  # Temporarily disabled - S3 permissions issue
  # access_logs {
  #   bucket  = aws_s3_bucket.alb_logs.bucket
  #   enabled = true
  # }

  tags = {
    Name   = "${local.tenant_prefix}-alb"
    Tenant = var.tenant_name
  }
}

# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${local.tenant_prefix}-alb-sg"
  description = "Security group for ${var.tenant_name} ALB"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name   = "${local.tenant_prefix}-alb-sg"
    Tenant = var.tenant_name
  }
}

# S3 bucket for ALB logs
resource "aws_s3_bucket" "alb_logs" {
  bucket = "${local.tenant_prefix}-alb-logs"

  tags = {
    Name   = "${local.tenant_prefix}-alb-logs"
    Tenant = var.tenant_name
  }
}

resource "aws_s3_bucket_public_access_block" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_id
      sse_algorithm     = "aws:kms"
    }
  }
}

# S3 bucket policy for ALB logs
data "aws_elb_service_account" "main" {}

# Current AWS account for IAM policies
data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = data.aws_elb_service_account.main.arn
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/*"
      }
    ]
  })
}

# ALB Target Group
resource "aws_lb_target_group" "django" {
  name     = "${local.tenant_prefix}-django"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200,301,302"
    path                = "/admin/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  deregistration_delay = 30

  tags = {
    Name   = "${local.tenant_prefix}-django"
    Tenant = var.tenant_name
  }
}

# ALB Listener
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.tenant.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.django.arn
  }

  tags = {
    Name   = "${local.tenant_prefix}-https"
    Tenant = var.tenant_name
  }
}

# HTTP to HTTPS redirect
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.tenant.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = {
    Name   = "${local.tenant_prefix}-http"
    Tenant = var.tenant_name
  }
}

# Route53 record for tenant subdomain
resource "aws_route53_record" "tenant" {
  zone_id = var.route53_zone_id
  name    = "${var.tenant_config.subdomain}.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.tenant.dns_name
    zone_id                = aws_lb.tenant.zone_id
    evaluate_target_health = true
  }
}

# Associate WAF with ALB (if in production)
resource "aws_wafv2_web_acl_association" "tenant" {
  count = var.environment == "production" ? 1 : 0

  resource_arn = aws_lb.tenant.arn
  web_acl_arn  = var.waf_web_acl_id
}
