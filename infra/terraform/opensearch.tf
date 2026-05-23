resource "aws_opensearch_domain" "this" {
  domain_name    = "${local.app_name}-${var.environment}"
  engine_version = "OpenSearch_2.13"

  cluster_config {
    instance_type  = "m6g.large.search"
    instance_count = 2
    zone_awareness_enabled = true
    zone_awareness_config {
      availability_zone_count = 2
    }
  }

  ebs_options {
    ebs_enabled = true
    volume_size = var.opensearch_volume_gb
    volume_type = "gp3"
  }

  node_to_node_encryption { enabled = true }
  encrypt_at_rest         { enabled = true }
  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  # In prod this would also configure fine-grained access control,
  # advanced security, SAML/Cognito, etc. Kept minimal here.
  tags = local.common_tags
}
