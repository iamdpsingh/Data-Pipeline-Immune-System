# ==============================================================================
# Data Pipeline Immune System — Terraform Variables
# ==============================================================================

variable "project_id" {
  description = "The GCP Project ID where resources will be provisioned."
  type        = string
  default     = "dpis-dev"
}

variable "region" {
  description = "The default GCP region for resources (Cloud Run, Buckets, Datasets)."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment: dev, staging, or production."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "dataset_location" {
  description = "Geographic location for BigQuery datasets (e.g., US, us-central1)."
  type        = string
  default     = "US"
}

variable "source_bucket_name" {
  description = "Override name for the source ingestion GCS bucket. Defaults to dpis-<env>-source."
  type        = string
  default     = ""
}

variable "bronze_bucket_name" {
  description = "Override name for the bronze raw staging GCS bucket. Defaults to dpis-<env>-bronze."
  type        = string
  default     = ""
}

variable "quarantine_bucket_name" {
  description = "Override name for the quarantine dead-letter GCS bucket. Defaults to dpis-<env>-quarantine."
  type        = string
  default     = ""
}

variable "cloud_run_min_instances" {
  description = "Minimum number of Cloud Run instances (0 for dev/staging, 1+ for prod)."
  type        = number
  default     = 0
}

variable "cloud_run_max_instances" {
  description = "Maximum number of Cloud Run instances allowed to scale."
  type        = number
  default     = 5
}

variable "cloud_run_image" {
  description = "Container image URI for the Immune System service."
  type        = string
  default     = "gcr.io/dpis-dev/immune-system:latest"
}

variable "alerts_slack_webhook" {
  description = "Optional Slack webhook URL stored in Secret Manager for incident notifications."
  type        = string
  default     = "placeholder-webhook-configure-in-secrets"
  sensitive   = true
}
