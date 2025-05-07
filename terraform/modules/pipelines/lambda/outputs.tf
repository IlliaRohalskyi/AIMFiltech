output "lambda_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.container_lambda.function_name
}