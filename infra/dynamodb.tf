resource "aws_dynamodb_table" "rate_limits" {
  name         = "${var.project}-rate-limits"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ip"

  attribute {
    name = "ip"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = { Name = "${var.project}-rate-limits" }
}

resource "aws_dynamodb_table" "usage_log" {
  name         = "${var.project}-usage-log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "username"
  range_key    = "timestamp"

  attribute {
    name = "username"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  tags = { Name = "${var.project}-usage-log" }
}
