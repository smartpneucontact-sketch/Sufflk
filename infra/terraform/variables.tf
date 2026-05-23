variable "aws_region" {
  description = "AWS region for the deployment."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "staging | prod"
  type        = string
}

variable "image_tag" {
  description = "Container image tag to deploy (typically the git SHA)."
  type        = string
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for the agent loop."
  type        = string
  default     = "anthropic.claude-sonnet-4-6-v1:0"
}

variable "opensearch_volume_gb" {
  description = "EBS volume size for the OpenSearch data nodes."
  type        = number
  default     = 50
}
