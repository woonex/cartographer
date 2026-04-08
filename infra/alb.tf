resource "aws_lb" "main" {
  name               = "${var.project}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = { Name = "${var.project}-alb" }
}

# ── Target Groups ─────────────────────────────────────────────────────────────

resource "aws_lb_target_group" "frontend" {
  name        = "${var.project}-frontend"
  port        = 8005
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
  }

  tags = { Name = "${var.project}-frontend-tg" }
}

resource "aws_lb_target_group" "ingestion" {
  name        = "${var.project}-ingestion"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
  }

  tags = { Name = "${var.project}-ingestion-tg" }
}

# ── Listener ──────────────────────────────────────────────────────────────────

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  # Default: send all traffic to frontend
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# /admin* is restricted to your IP — returns 403 to everyone else
resource "aws_lb_listener_rule" "admin_allow" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 8

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  condition {
    path_pattern {
      values = ["/admin", "/admin/*"]
    }
  }

  condition {
    source_ip {
      values = [var.my_ip_cidr]
    }
  }
}

resource "aws_lb_listener_rule" "admin_deny" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 9

  action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Forbidden"
      status_code  = "403"
    }
  }

  condition {
    path_pattern {
      values = ["/admin", "/admin/*"]
    }
  }
}

# /ingest* is restricted to your IP — returns 403 to everyone else
resource "aws_lb_listener_rule" "ingestion" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ingestion.arn
  }

  condition {
    path_pattern {
      values = ["/ingest", "/ingest/*"]
    }
  }

  condition {
    source_ip {
      values = [var.my_ip_cidr]
    }
  }
}
