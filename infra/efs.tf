resource "aws_efs_file_system" "qdrant" {
  creation_token = "${var.project}-qdrant"
  encrypted      = true

  tags = { Name = "${var.project}-qdrant-efs" }
}

resource "aws_efs_mount_target" "qdrant" {
  count           = 2
  file_system_id  = aws_efs_file_system.qdrant.id
  subnet_id       = aws_subnet.public[count.index].id
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "qdrant" {
  file_system_id = aws_efs_file_system.qdrant.id

  root_directory {
    path = "/qdrant-storage"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = { Name = "${var.project}-qdrant-ap" }
}
