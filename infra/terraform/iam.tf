data "aws_iam_policy_document" "task_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task" {
  name               = "${local.app_name}-${var.environment}-task"
  assume_role_policy = data.aws_iam_policy_document.task_assume.json
}

data "aws_iam_policy_document" "task_policy" {
  statement {
    sid     = "BedrockInvokeClaude"
    effect  = "Allow"
    actions = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = [
      "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}",
    ]
  }

  statement {
    sid    = "OpenSearchAccess"
    effect = "Allow"
    actions = [
      "es:ESHttpGet",
      "es:ESHttpPost",
      "es:ESHttpPut",
      "es:ESHttpDelete",
    ]
    resources = ["${aws_opensearch_domain.this.arn}/*"]
  }

  statement {
    sid    = "Logs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:CreateLogGroup",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "task" {
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_policy.json
}

resource "aws_iam_role" "execution" {
  name               = "${local.app_name}-${var.environment}-exec"
  assume_role_policy = data.aws_iam_policy_document.task_assume.json
}

resource "aws_iam_role_policy_attachment" "execution_attach" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
