# IAM Role for AWS Batch Service
resource "aws_iam_role" "batch_service_role" {
  name = "batch-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "batch.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_service_role_ecs_delete" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = aws_iam_policy.batch_service_ecs_delete.arn
}

resource "aws_iam_policy" "batch_service_ecs_delete" {
  name   = "BatchServiceECSDeletePolicy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "ecs:DeleteCluster",
        Resource = "arn:aws:ecs:${var.aws_region}:${var.aws_account_id}:cluster/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_service_role_logs" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = aws_iam_policy.batch_service_logs_policy.arn
}

resource "aws_iam_policy" "batch_service_logs_policy" {
  name   = "BatchServiceLogsPolicy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group::log_stream"
      }
    ]
  })
}

# IAM Role Policy Attachment for AWS Batch Service Role
resource "aws_iam_role_policy_attachment" "batch_service_role_policy" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# Batch Compute Environment
resource "aws_batch_compute_environment" "compute_environment" {
  compute_environment_name = "compute-environment"
  type                     = "MANAGED"

  compute_resources {
    type              = "FARGATE"
    max_vcpus         = 5
    subnets           = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  service_role = aws_iam_role.batch_service_role.arn

  depends_on = [
    aws_iam_role.batch_service_role,
    aws_iam_role_policy_attachment.batch_service_role_policy,
    aws_iam_role_policy_attachment.batch_service_role_ecs_delete,
    aws_iam_role_policy_attachment.batch_service_role_logs
    ]
}

# Batch Job Queue
resource "aws_batch_job_queue" "job_queue" {
  name                 = "transform-job-queue"
  state                = "ENABLED"
  priority             = 1
    compute_environment_order {
        order                 = 1
        compute_environment   = aws_batch_compute_environment.compute_environment.arn
    }
}

# IAM Role for Job Execution
resource "aws_iam_role" "execution_role" {
  name = "batch-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Role Policy Attachment for Job Execution Role
resource "aws_iam_role_policy_attachment" "execution_role_policy" {
  role       = aws_iam_role.execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Batch Job Definition
resource "aws_batch_job_definition" "job_definition" {
  name          = "training-transform-job-definition"
  type          = "container"

  container_properties = jsonencode({
    image        = "${var.repository_url}:${var.image_tag}"
    vcpus        = 256
    memory       = 512
    command      = ["bash", "-c", "python3 app/src/batch_jobs/batch_worker.py"]
    executionRoleArn = aws_iam_role.execution_role.arn
  })
}