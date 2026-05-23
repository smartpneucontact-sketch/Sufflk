# Terraform — Site Copilot deploy stub

Sketch of the AWS deploy. Not production-ready; intentionally minimal so the
shape is reviewable end-to-end:

- `main.tf` — provider, locals, common tags
- `network.tf` — VPC, subnets (assumes a shared VPC by name in prod; this stub uses default VPC)
- `ecr.tf` — image registry
- `ecs.tf` — Fargate service + task def + ALB
- `opensearch.tf` — OpenSearch domain with kNN enabled (vector + lexical)
- `iam.tf` — task role with `bedrock:InvokeModel` for Claude on Bedrock
- `variables.tf` — inputs
- `outputs.tf` — ALB DNS, OpenSearch endpoint, ECR URL

## Why this shape

The JD calls for **AWS Bedrock + OpenSearch + GitHub Actions + Terraform**.
This deploy plan maps every named component to a Terraform resource so a
reviewer can see the path from local demo -> production:

| Local                 | Production                              |
| --------------------- | --------------------------------------- |
| Anthropic SDK         | Bedrock `anthropic.claude-sonnet-4-6-v1`|
| BM25 + Chroma         | OpenSearch hybrid (BM25 + kNN)          |
| Uvicorn on 8000       | ECS Fargate behind ALB                  |
| JSONL traces on disk  | CloudWatch Logs -> Databricks bronze    |

## How to apply (when ready)

```bash
cd infra/terraform
terraform init
terraform plan -var environment=staging -var image_tag=latest
terraform apply -var environment=staging -var image_tag=latest
```
