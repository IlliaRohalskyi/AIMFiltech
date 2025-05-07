output "batch_job_name" {
  description = "Name of the AWS Batch job"
  value       = aws_batch_job_definition.job_definition.name
}

output "batch_job_definition_arn" {
  description = "ARN of the AWS Batch job definition"
  value       = aws_batch_job_definition.job_definition.arn
}

output "batch_job_queue_arn" {
  description = "ARN of the AWS Batch job queue"
  value       = aws_batch_job_queue.job_queue.arn
}