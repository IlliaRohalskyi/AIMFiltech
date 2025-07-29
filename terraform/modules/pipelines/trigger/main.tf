# S3 event notification configuration
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = var.s3_bucket_name
  
  eventbridge = true
}

# EventBridge rule to capture S3 events and trigger Step Function
resource "aws_cloudwatch_event_rule" "s3_ml_upload_rule" {
  name        = "s3-ml-upload-rule"
  description = "Capture S3 object creation events in train/ and predict/ folders"
  
  event_pattern = jsonencode({
    source      = ["aws.s3"],
    detail-type = ["Object Created"],
    detail      = {
      bucket = {
        name = [var.s3_bucket_name]
      },
      object = {
        key = [
          {
            prefix = "raw/train/"
          },
          {
            prefix = "raw/predict/"
          }
        ]
      }
    }
  })
}

# EventBridge target for the rule
resource "aws_cloudwatch_event_target" "s3_step_function_target" {
  rule      = aws_cloudwatch_event_rule.s3_ml_upload_rule.name
  arn       = var.step_function_arn
  role_arn  = aws_iam_role.eventbridge_role.arn
}

# IAM role for EventBridge to invoke Step Function
resource "aws_iam_role" "eventbridge_role" {
  name = "eventbridge-trigger-step-function-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "events.amazonaws.com"
      }
    }]
  })
}

# IAM policy to allow EventBridge to start Step Function execution
resource "aws_iam_policy" "eventbridge_policy" {
  name = "eventbridge-trigger-step-function-policy"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = "states:StartExecution",
      Resource = var.step_function_arn
    }]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "eventbridge_policy_attachment" {
  role       = aws_iam_role.eventbridge_role.name
  policy_arn = aws_iam_policy.eventbridge_policy.arn
}