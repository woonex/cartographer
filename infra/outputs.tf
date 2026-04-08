output "alb_url" {
  description = "Public URL for the application"
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecr_urls" {
  description = "ECR repository URLs (use these in your docker push commands)"
  value       = { for k, v in aws_ecr_repository.services : k => v.repository_url }
}

output "ecs_cluster" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}
