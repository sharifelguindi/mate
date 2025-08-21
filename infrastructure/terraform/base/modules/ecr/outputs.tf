output "repository_urls" {
  value = {
    for k, v in aws_ecr_repository.repos : k => v.repository_url
  }
}

output "repository_arns" {
  value = {
    for k, v in aws_ecr_repository.repos : k => v.arn
  }
}

output "registry_id" {
  value = values(aws_ecr_repository.repos)[0].registry_id
}

output "ecr_registry" {
  value = "${values(aws_ecr_repository.repos)[0].registry_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com"
}

data "aws_region" "current" {}