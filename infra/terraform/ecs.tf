# Minimal Fargate task + service behind an ALB. Stub — production hardening
# (autoscaling, container insights, deployment controller, alarms) deliberately
# omitted to keep this file reviewable.

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_ecs_cluster" "this" {
  name = "${local.app_name}-${var.environment}"
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.app_name}/${var.environment}"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${local.app_name}-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = local.app_name
      image     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [{ containerPort = 8000, protocol = "tcp" }]
      environment = [
        { name = "SITE_COPILOT_MODEL", value = var.bedrock_model_id },
        { name = "SITE_COPILOT_RETRIEVER", value = "hybrid" },
        { name = "OPENSEARCH_ENDPOINT", value = aws_opensearch_domain.this.endpoint },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "app"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -fsS http://localhost:8000/healthz || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 15
      }
    }
  ])
}

resource "aws_security_group" "service" {
  name        = "${local.app_name}-${var.environment}-svc"
  description = "Site Copilot service SG"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_service" "app" {
  name            = "${local.app_name}-${var.environment}"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = true
  }
}
