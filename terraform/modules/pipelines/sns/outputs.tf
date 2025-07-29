output "sns_topic_arn" {
  value = aws_sns_topic.ml_monitoring_alerts.arn
  description = "ARN of the SNS topic for ML monitoring alerts"
}