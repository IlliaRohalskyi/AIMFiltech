# SNS Topic for ML monitoring alerts
resource "aws_sns_topic" "ml_monitoring_alerts" {
  name = "ml-monitoring-alerts"
}

# SNS Topic Policy
resource "aws_sns_topic_policy" "ml_monitoring_alerts_policy" {
  arn = aws_sns_topic.ml_monitoring_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
        Action = "sns:Publish"
        Resource = aws_sns_topic.ml_monitoring_alerts.arn
      }
    ]
  })
}