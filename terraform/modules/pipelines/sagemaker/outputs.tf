output "sagemaker_role_arn" {
  description = "ARN of the SageMaker execution role"
  value       = aws_iam_role.sagemaker_execution_role.arn
}

output "sagemaker_model_name" {
  description = "Name of the SageMaker model for Batch Transform"
  value       = aws_sagemaker_model.inference_model.name
}