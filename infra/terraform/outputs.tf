output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app.name
}

output "opensearch_endpoint" {
  value = aws_opensearch_domain.this.endpoint
}

output "log_group" {
  value = aws_cloudwatch_log_group.app.name
}
