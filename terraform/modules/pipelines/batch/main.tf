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

# IAM Role for Job Task (for application permissions)
resource "aws_iam_role" "job_role" {
  name = "batch-job-role"

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

# S3 Policy for Job Role
resource "aws_iam_policy" "job_s3_policy" {
  name   = "job-s3-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect: "Allow",
        Action: [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucketVersions",
          "s3:PutObjectTagging",
          "s3:GetObjectVersion"
        ],
        Resource: [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "execution_role_ecr_policy" {
  name   = "execution-role-ecr-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect: "Allow",
        Action: [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ],
        Resource: "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "execution_role_ecr_policy_attachment" {
  role       = aws_iam_role.execution_role.name
  policy_arn = aws_iam_policy.execution_role_ecr_policy.arn
}

# Attach S3 policy to Job Role
resource "aws_iam_role_policy_attachment" "job_role_s3_policy_attachment" {
  role       = aws_iam_role.job_role.name
  policy_arn = aws_iam_policy.job_s3_policy.arn
}

# Batch Job Definition
resource "aws_batch_job_definition" "job_definition" {
  name          = "training-transform-job-definition"
  type          = "container"
  platform_capabilities = ["FARGATE"]

  container_properties = jsonencode({
    image        = "${var.repository_url}:${var.image_tag}"
    fargatePlatformConfiguration = {
      platformVersion = "LATEST"
    }
    resourceRequirements = [
      {
        type  = "VCPU"
        value = "0.25"
      },
      {
        type  = "MEMORY"
        value = "512"
      }
    ]
    command      = ["bash", "-c", "python3 app/src/batch_jobs/batch_worker.py"]
    executionRoleArn = aws_iam_role.execution_role.arn,
    jobRoleArn = aws_iam_role.job_role.arn
  })
}