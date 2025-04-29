resource "aws_ecs_cluster" "this" {
  name = "aimfiltech-cluster"
}

resource "aws_cloudwatch_log_group" "ecs" {
  name = "/ecs/master"
}

resource "aws_ecs_task_definition" "master_task" {
  family                   = "master-task"
  cpu                      = "256"
  memory                   = "512"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "master"
      image     = "${var.repository_url}:${var.image_tag}"
      essential = true
      cpu       = 256
      memory    = 512
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_iam_role" "ecs_execution_role" {
  name = "ecs-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name = "ecs-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

data "aws_iam_policy_document" "ecs_task_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucketVersions",
      "s3:PutObjectTagging",
      "s3:GetObjectVersion"
    ]
    resources = [
      "arn:aws:s3:::${var.s3_bucket_name}/processed/*",
      "arn:aws:s3:::${var.s3_bucket_name}/raw/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "batch:SubmitJob",
      "batch:DescribeJobs",
      "batch:TerminateJob",
      "batch:ListJobs"
    ]

    resources = [
      "arn:aws:batch:${var.aws_region}:${var.aws_account_id}:job-queue/transform-job-queue",
      "arn:aws:batch:${var.aws_region}:${var.aws_account_id}:job-definition/training-transform-job-definition",
      "arn:aws:batch:${var.aws_region}:${var.aws_account_id}:compute-environment/compute-environment"
    ]
  }
}

resource "aws_iam_policy" "ecs_task_policy" {
  name   = "ecs-task-policy"
  policy = data.aws_iam_policy_document.ecs_task_policy.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_policy_attach" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}