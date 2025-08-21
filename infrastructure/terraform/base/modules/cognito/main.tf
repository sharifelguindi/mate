# Cognito User Pool Module

resource "aws_cognito_user_pool" "main" {
  name = "mate-${var.environment}"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  tags = {
    Name        = "mate-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = var.domain
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "aws_cognito_user_pool_client" "main" {
  name         = "mate-${var.environment}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]

  callback_urls = [
    "https://${var.domain}.sociant.ai/auth/callback",
    "http://localhost:8000/auth/callback"
  ]

  logout_urls = [
    "https://${var.domain}.sociant.ai/logout",
    "http://localhost:8000/logout"
  ]

  supported_identity_providers = ["COGNITO"]

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]
}
