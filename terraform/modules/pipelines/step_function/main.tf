# Step Function Role
resource "aws_iam_role" "step_function_role" {
  name = "step-function-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

# Step Function Policy
resource "aws_iam_policy" "step_function_policy" {
  name   = "step-function-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect: "Allow",
        Action: [
          "lambda:InvokeFunction",
          "batch:SubmitJob",
          "batch:DescribeJobs",
          "s3:GetObject",
          "events:PutRule",
          "events:PutTargets",
          "events:DeleteRule",
          "events:RemoveTargets"
        ],
        Resource: "*"
      }
    ]
  })
}

# Attach Policy to Step Function Role
resource "aws_iam_role_policy_attachment" "step_function_policy_attachment" {
  role       = aws_iam_role.step_function_role.name
  policy_arn = aws_iam_policy.step_function_policy.arn
}

# Step Function
resource "aws_sfn_state_machine" "step_function" {
  name     = "training-pipeline-step-function"
  role_arn = aws_iam_role.step_function_role.arn

  definition = jsonencode({
    Comment: "State machine to process data in chunks using AWS Batch",
    StartAt: "SplitData",
    States: {
      SplitData: {
        Type: "Task",
        Resource: "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.split_data_lambda_name}",
        ResultPath: "$.split_result",
        Next: "MapState"
      },
      MapState: {
        Type: "Map",
        ItemsPath: "$.split_result.chunk_keys",
        Iterator: {
          StartAt: "SubmitBatchJob",
          States: {
            SubmitBatchJob: {
              Type: "Task",
              Resource: "arn:aws:states:::batch:submitJob.sync",
              Parameters: {
                JobName: var.batch_job_name,
                JobQueue: var.batch_job_queue_arn,
                JobDefinition: var.batch_job_definition_arn,
                ContainerOverrides: {
                  Environment: [
                    {
                      Name: "S3_BUCKET",
                      Value: var.s3_bucket_name
                    },
                    {
                      Name: "CHUNK_KEY",
                      Value: "$$.Map.Item.Value"
                    },
                    {
                      Name: "RUN_ID",
                      Value: "$.split_result.run_id"
                    },
                    {
                      Name: "VERSION_ID",
                      Value: "$.split_result.version_id"
                    }
                  ]
                }
              },
              End: true
            }
          }
        },
        End: true
      }
    }
  })
}