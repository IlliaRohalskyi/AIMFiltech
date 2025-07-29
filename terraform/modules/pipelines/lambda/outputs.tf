output "lambda_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.container_lambda.function_name
}

output "post_process_lambda_name" {
  description = "Name of the post-process Lambda function"
  value       = aws_lambda_function.post_process_lambda.function_name
}

output "monitoring_lambda_name" {
  description = "Name of the monitoring Lambda function"
  value       = aws_lambda_function.monitoring_lambda.function_name
}