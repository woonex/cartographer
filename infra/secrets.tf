resource "aws_secretsmanager_secret" "groq_api_key" {
  name                    = "${var.project}/groq-api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "groq_api_key" {
  secret_id     = aws_secretsmanager_secret.groq_api_key.id
  secret_string = var.groq_api_key
}

resource "aws_secretsmanager_secret" "frontend_auth_users" {
  name                    = "${var.project}/frontend-auth-users"
  recovery_window_in_days = 0
  # Populate this secret manually after apply — Terraform does not manage the value.
  # See "Managing users" in README.md.
}
