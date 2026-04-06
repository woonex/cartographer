resource "aws_ecs_cluster" "main" {
  name = var.project

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project}"
  retention_in_days = 7
}

# ── Cloud Map (service discovery) ─────────────────────────────────────────────
# Services resolve each other via DNS within the VPC:
#   qdrant.cartographer.local:6333
#   query.cartographer.local:8002
#   vehicle-library.cartographer.local:8003
#   specification-library.cartographer.local:8004

resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "cartographer.local"
  description = "Internal DNS for Cartographer services"
  vpc         = aws_vpc.main.id
}

resource "aws_service_discovery_service" "qdrant" {
  name = "qdrant"
  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.main.id
    routing_policy = "MULTIVALUE"
    dns_records {
      ttl  = 10
      type = "A"
    }
  }
  health_check_custom_config { failure_threshold = 1 }
}

resource "aws_service_discovery_service" "query" {
  name = "query"
  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.main.id
    routing_policy = "MULTIVALUE"
    dns_records {
      ttl  = 10
      type = "A"
    }
  }
  health_check_custom_config { failure_threshold = 1 }
}

resource "aws_service_discovery_service" "vehicle_library" {
  name = "vehicle-library"
  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.main.id
    routing_policy = "MULTIVALUE"
    dns_records {
      ttl  = 10
      type = "A"
    }
  }
  health_check_custom_config { failure_threshold = 1 }
}

resource "aws_service_discovery_service" "specification_library" {
  name = "specification-library"
  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.main.id
    routing_policy = "MULTIVALUE"
    dns_records {
      ttl  = 10
      type = "A"
    }
  }
  health_check_custom_config { failure_threshold = 1 }
}

# ── Shared log config helper ──────────────────────────────────────────────────

locals {
  log_config = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
      "awslogs-region"        = var.aws_region
      "awslogs-stream-prefix" = "ecs"
    }
  }
}

# ── Qdrant ────────────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "qdrant" {
  family                   = "${var.project}-qdrant"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  volume {
    name = "qdrant-storage"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.qdrant.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.qdrant.id
        iam             = "DISABLED"
      }
    }
  }

  container_definitions = jsonencode([{
    name      = "qdrant"
    image     = "qdrant/qdrant:latest"
    essential = true
    portMappings = [{ containerPort = 6333, protocol = "tcp" }]
    mountPoints = [{
      sourceVolume  = "qdrant-storage"
      containerPath = "/qdrant/storage"
      readOnly      = false
    }]
    logConfiguration = local.log_config
  }])
}

resource "aws_ecs_service" "qdrant" {
  name            = "${var.project}-qdrant"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.qdrant.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  service_registries {
    registry_arn = aws_service_discovery_service.qdrant.arn
  }
}

# ── Vehicle Library ───────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "vehicle_library" {
  family                   = "${var.project}-vehicle-library"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "vehicle-library"
    image     = "${aws_ecr_repository.services["vehicle-library"].repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8003, protocol = "tcp" }]
    logConfiguration = local.log_config
  }])
}

resource "aws_ecs_service" "vehicle_library" {
  name            = "${var.project}-vehicle-library"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.vehicle_library.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  service_registries {
    registry_arn = aws_service_discovery_service.vehicle_library.arn
  }
}

# ── Specification Library ─────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "specification_library" {
  family                   = "${var.project}-specification-library"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "specification-library"
    image     = "${aws_ecr_repository.services["specification-library"].repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8004, protocol = "tcp" }]
    logConfiguration = local.log_config
  }])
}

resource "aws_ecs_service" "specification_library" {
  name            = "${var.project}-specification-library"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.specification_library.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  service_registries {
    registry_arn = aws_service_discovery_service.specification_library.arn
  }
}

# ── Query ─────────────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "query" {
  family                   = "${var.project}-query"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "query"
    image     = "${aws_ecr_repository.services["query"].repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8002, protocol = "tcp" }]
    environment = [
      { name = "QUERY_VECTOR_STORE_URL",           value = "http://qdrant.cartographer.local:6333" },
      { name = "QUERY_VEHICLE_LIBRARY_URL",        value = "http://vehicle-library.cartographer.local:8003" },
      { name = "QUERY_SPECIFICATIONS_LIBRARY_URL", value = "http://specification-library.cartographer.local:8004" },
    ]
    secrets = [
      { name = "GROQ_API_KEY", valueFrom = aws_secretsmanager_secret.groq_api_key.arn }
    ]
    logConfiguration = local.log_config
  }])
}

resource "aws_ecs_service" "query" {
  name            = "${var.project}-query"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.query.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  service_registries {
    registry_arn = aws_service_discovery_service.query.arn
  }

  depends_on = [aws_ecs_service.qdrant, aws_ecs_service.vehicle_library, aws_ecs_service.specification_library]
}

# ── Ingestion ─────────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "ingestion" {
  family                   = "${var.project}-ingestion"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "ingestion"
    image     = "${aws_ecr_repository.services["ingestion"].repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8001, protocol = "tcp" }]
    environment = [
      { name = "INGESTION_VECTOR_STORE_URL", value = "http://qdrant.cartographer.local:6333" },
    ]
    logConfiguration = local.log_config
  }])
}

resource "aws_ecs_service" "ingestion" {
  name            = "${var.project}-ingestion"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ingestion.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ingestion.arn
    container_name   = "ingestion"
    container_port   = 8001
  }

  depends_on = [aws_ecs_service.qdrant, aws_lb_listener.http]
}

# ── Frontend ──────────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "frontend"
    image     = "${aws_ecr_repository.services["frontend"].repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8005, protocol = "tcp" }]
    environment = [
      { name = "FRONTEND_QUERY_URL",           value = "http://query.cartographer.local:8002" },
      { name = "FRONTEND_VEHICLE_LIBRARY_URL", value = "http://vehicle-library.cartographer.local:8003" },
      { name = "FRONTEND_DYNAMODB_TABLE",      value = aws_dynamodb_table.rate_limits.name },
      { name = "FRONTEND_USAGE_LOG_TABLE",     value = aws_dynamodb_table.usage_log.name },
      { name = "FRONTEND_DYNAMODB_REGION",     value = var.aws_region },
      { name = "FRONTEND_AUTH_USERS_SECRET",   value = aws_secretsmanager_secret.frontend_auth_users.name },
    ]
    secrets = []
    logConfiguration = local.log_config
  }])
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.project}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 8005
  }

  depends_on = [aws_ecs_service.query, aws_lb_listener.http]
}
