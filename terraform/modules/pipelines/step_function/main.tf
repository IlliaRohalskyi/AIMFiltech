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
          "ecs:DescribeClusters",
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

resource "aws_sfn_state_machine" "step_function" {
  name     = "training-pipeline-step-function"
  role_arn = aws_iam_role.step_function_role.arn

  definition = <<EOF
{
  "Comment": "State machine to process data in chunks using AWS Batch",
  "StartAt": "ProcessS3Event",
  "States": {
    "ProcessS3Event": {
      "Type": "Pass",
      "Parameters": {
        "bucket": "${var.s3_bucket_name}",
        "key.$": "$.detail.object.key",
        "version_id.$": "$.detail.object.version-id",
        "run_id.$": "$$.Execution.Name"
      },
      "Next": "SplitData"
    },
    "SplitData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.split_data_lambda_name}",
      "ResultPath": "$.split_result",
      "Next": "CheckSplitResults"
    },
    "CheckSplitResults": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.split_result.chunk_keys",
          "IsPresent": true,
          "Next": "MapState"
        }
      ],
      "Default": "SplitFailure"
    },
    "SplitFailure": {
      "Type": "Fail",
      "Error": "NoChunkKeysFound",
      "Cause": "The SplitData Lambda did not produce any chunk keys to process"
    },
    "MapState": {
      "Type": "Map",
      "ItemsPath": "$.split_result.chunk_keys",
      "ResultPath": "$.batch_results",
      "Parameters": {
        "chunk_key.$": "$$.Map.Item.Value",
        "run_id.$": "$.split_result.run_id",
        "version_id.$": "$.split_result.version_id"
      },
      "Iterator": {
        "StartAt": "SubmitBatchJob",
        "States": {
          "SubmitBatchJob": {
            "Type": "Task",
            "Resource": "arn:aws:states:::batch:submitJob.sync",
            "Parameters": {
              "JobName": "${var.batch_job_name}",
              "JobQueue": "${var.batch_job_queue_arn}",
              "JobDefinition": "${var.batch_job_definition_arn}",
              "ContainerOverrides": {
                "Environment": [
                  {
                    "Name": "S3_BUCKET", 
                    "Value": "${var.s3_bucket_name}"
                  },
                  {
                    "Name": "S3_KEY",
                    "Value.$": "$.chunk_key"
                  },
                  {
                    "Name": "RUN_ID",
                    "Value.$": "$.run_id"
                  },
                  {
                    "Name": "version_id",
                    "Value.$": "$.version_id"
                  }
                ]
              }
            },
            "ResultPath": "$.batch_result",
            "End": true
          }
        }
      },
      "Next": "CombineResults"
    },
    "CombineResults": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.post_process_lambda_name}",
      "Parameters": {
        "bucket": "${var.s3_bucket_name}",
        "run_id.$": "$.split_result.run_id",
        "version_id.$": "$.split_result.version_id"
      },
      "End": true
    }
  }
}
EOF
}