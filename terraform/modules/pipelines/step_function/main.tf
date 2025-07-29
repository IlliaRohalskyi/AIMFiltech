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
          "s3:PutObject",
          "events:PutRule",
          "events:PutTargets",
          "events:DeleteRule",
          "events:RemoveTargets",
          "sagemaker:CreateTrainingJob",
          "sagemaker:DescribeTrainingJob",
          "sagemaker:StopTrainingJob",
          "sagemaker:CreateTransformJob",
          "sagemaker:DescribeTransformJob",
          "sagemaker:StopTransformJob",
          "sagemaker:AddTags",
          "iam:PassRole",
          "sns:Publish"
        ],
        Resource: "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "step_function_policy_attachment" {
  role       = aws_iam_role.step_function_role.name
  policy_arn = aws_iam_policy.step_function_policy.arn
}

resource "aws_sfn_state_machine" "step_function" {
  name     = "training-prediction-pipeline-step-function"
  role_arn = aws_iam_role.step_function_role.arn

  definition = <<EOF
{
  "Comment": "State machine to process data and train/predict ML models using SageMaker with identical transformations",
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
      "Next": "DetermineTaskType"
    },
    "DetermineTaskType": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.key",
          "StringMatches": "raw/train/*",
          "Next": "SetTrainingTask"
        },
        {
          "Variable": "$.key",
          "StringMatches": "raw/predict/*",
          "Next": "SetPredictionTask"
        }
      ],
      "Default": "UnsupportedFolder"
    },
    "UnsupportedFolder": {
      "Type": "Fail",
      "Error": "UnsupportedS3Folder",
      "Cause": "File must be uploaded to train/ or predict/ folder"
    },
    "SetTrainingTask": {
      "Type": "Pass",
      "Parameters": {
        "bucket.$": "$.bucket",
        "key.$": "$.key",
        "version_id.$": "$.version_id",
        "run_id.$": "$.run_id",
        "task_type": "train"
      },
      "Next": "SplitData"
    },
    "SetPredictionTask": {
      "Type": "Pass",
      "Parameters": {
        "bucket.$": "$.bucket",
        "key.$": "$.key",
        "version_id.$": "$.version_id",
        "run_id.$": "$.run_id",
        "task_type": "predict"
      },
      "Next": "SplitData"
    },
    "SplitData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.split_data_lambda_name}",
      "ResultPath": "$.split_result",
      "Next": "CheckSplitResults",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error_info",
          "Next": "NotifyFailure"
        }
      ]
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
        "version_id.$": "$.split_result.version_id",
        "task_type.$": "$.task_type"
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
            "End": true,
            "Catch": [
              {
                "ErrorEquals": ["States.ALL"],
                "ResultPath": "$.error_info",
                "Next": "BatchJobFailure"
              }
            ]
          },
          "BatchJobFailure": {
            "Type": "Task",
            "Resource": "arn:aws:states:::sns:publish",
            "Parameters": {
              "TopicArn": "${var.alert_sns_topic_arn}",
              "Message.$": "States.Format('DATA PROCESSING FAILED - Run ID: {} | Operation: Batch Job | Task: {} | Chunk: {}', $.run_id, $.task_type, $.chunk_key)",
              "Subject": "Data Processing Failed"
            },
            "End": true
          }
        }
      },
      "Next": "CombineResults",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error_info",
          "Next": "NotifyFailure"
        }
      ]
    },
    "CombineResults": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.post_process_lambda_name}",
      "Parameters": {
        "bucket": "${var.s3_bucket_name}",
        "run_id.$": "$.split_result.run_id",
        "version_id.$": "$.split_result.version_id"
      },
      "ResultPath": "$.combined_data",
      "Next": "RunSageMakerJob",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error_info",
          "Next": "NotifyFailure"
        }
      ]
    },
    "RunSageMakerJob": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.task_type",
          "StringEquals": "train",
          "Next": "RunTrainingJob"
        },
        {
          "Variable": "$.task_type",
          "StringEquals": "predict",
          "Next": "RunBatchTransformJob"
        }
      ],
      "Default": "UnsupportedTaskType"
    },
    "UnsupportedTaskType": {
      "Type": "Fail",
      "Error": "UnsupportedTaskType",
      "Cause": "Task type must be 'train' or 'predict'"
    },
    "RunTrainingJob": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sagemaker:createTrainingJob.sync",
      "Parameters": {
        "TrainingJobName.$": "States.Format('train-{}', States.ArrayGetItem(States.StringSplit($$.Execution.Name, '_'), 0))",
        "RoleArn": "${var.sagemaker_role_arn}",
        "AlgorithmSpecification": {
          "TrainingImage": "${var.repository_url}:${var.image_tag}",
          "TrainingInputMode": "File"
        },
        "ResourceConfig": {
          "InstanceType": "ml.m5.large",
          "InstanceCount": 1,
          "VolumeSizeInGB": 30
        },
        "InputDataConfig": [
          {
            "ChannelName": "train",
            "DataSource": {
              "S3DataSource": {
                "S3Uri.$": "$.combined_data.output_path",
                "S3DataType": "S3Prefix",
                "S3DataDistributionType": "FullyReplicated"
              }
            },
            "ContentType": "application/vnd.ms-excel"
          }
        ],
        "OutputDataConfig": {
          "S3OutputPath": "s3://${var.s3_bucket_name}/model-outputs/"
        },
        "Environment": {
          "MLFLOW_TRACKING_URI": "https://${var.mlflow_private_ip}",
          "SAGEMAKER_PROGRAM": "train"
        },
        "StoppingCondition": {
          "MaxRuntimeInSeconds": 7200
        },
        "VpcConfig": {
          "SecurityGroupIds": ["${var.sagemaker_security_group_id}"],
          "Subnets": ["${var.sagemaker_subnet_id}"]
        }
      },
      "ResultPath": "$.sagemaker_result",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error_info",
          "Next": "RunTrainingJobFailure"
        }
      ],
      "Next": "RunTrainingJobSuccess"
    },
    "RunTrainingJobSuccess": {
      "Type": "Pass",
      "End": true
    },
    "RunTrainingJobFailure": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "${var.alert_sns_topic_arn}",
        "Message.$": "States.Format('TRAINING JOB FAILED - Run ID: {} | Operation: SageMaker Training | Task: Train', $.split_result.run_id)",
        "Subject": "Training Job Failed"
      },
      "End": true
    },
    "RunBatchTransformJob": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sagemaker:createTransformJob.sync",
      "Parameters": {
        "TransformJobName.$": "States.Format('predict-{}', States.ArrayGetItem(States.StringSplit($$.Execution.Name, '_'), 0))",
        "ModelName": "${var.sagemaker_model_name}",
        "TransformInput": {
          "DataSource": {
            "S3DataSource": {
              "S3Uri.$": "$.combined_data.output_path",
              "S3DataType": "S3Prefix"
            }
          },
          "ContentType": "text/csv"
        },
        "TransformOutput": {
          "S3OutputPath.$": "States.Format('s3://{}/prediction-outputs/{}', '${var.s3_bucket_name}', $.split_result.run_id)"
        },
        "TransformResources": {
          "InstanceType": "ml.m5.large",
          "InstanceCount": 1
        },
        "Environment": {
          "MLFLOW_TRACKING_URI": "https://${var.mlflow_private_ip}",
          "SAGEMAKER_PROGRAM": "predict"
        }
      },
      "ResultPath": "$.sagemaker_result",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error_info",
          "Next": "RunBatchTransformJobFailure"
        }
      ],
      "Next": "RunBatchTransformJobSuccess"
    },
    "RunBatchTransformJobSuccess": {
      "Type": "Pass",
      "Next": "MonitorPredictions"
    },
    "RunBatchTransformJobFailure": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "${var.alert_sns_topic_arn}",
        "Message.$": "States.Format('PREDICTION JOB FAILED - Run ID: {} | Operation: SageMaker Batch Transform | Task: Predict', $.split_result.run_id)",
        "Subject": "Prediction Job Failed"
      },
      "End": true
    },
    "MonitorPredictions": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.monitoring_lambda_name}",
      "Parameters": {
        "s3_bucket": "${var.s3_bucket_name}",
        "s3_key.$": "States.Format('prediction-outputs/{}/combined_results.csv.out', $.split_result.run_id)",
        "mlflow_tracking_uri": "https://${var.mlflow_private_ip}",
        "sns_topic_arn": "${var.alert_sns_topic_arn}"
      },
      "ResultPath": "$.monitoring_result",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error_info",
          "Next": "NotifyFailure"
        }
      ],
      "End": true
    },
    "NotifyFailure": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "${var.alert_sns_topic_arn}",
        "Message.$": "States.Format('PIPELINE FAILED - Run ID: {} | Failed State: {} | Operation: Pipeline Infrastructure', $.split_result.run_id, $.State.Name)",
        "Subject": "Pipeline Infrastructure Failed"
      },
      "End": true
    }
  }
}
EOF
}