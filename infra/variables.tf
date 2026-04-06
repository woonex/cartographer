variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "cartographer"
}

variable "groq_api_key" {
  type      = string
  sensitive = true
}

variable "my_ip_cidr" {
  type        = string
  description = "Your public IP in CIDR notation (e.g. 1.2.3.4/32) — restricts /ingest endpoint access"
}
