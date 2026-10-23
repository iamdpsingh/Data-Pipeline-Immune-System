# ==============================================================================
# Data Pipeline Immune System — Main Terraform Infrastructure
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  source_bucket     = var.source_bucket_name != "" ? var.source_bucket_name : "dpis-${var.environment}-source"
  bronze_bucket     = var.bronze_bucket_name != "" ? var.bronze_bucket_name : "dpis-${var.environment}-bronze"
  quarantine_bucket = var.quarantine_bucket_name != "" ? var.quarantine_bucket_name : "dpis-${var.environment}-quarantine"
  
  control_dataset   = "dpis_${var.environment}"
  bronze_dataset    = "dpis_bronze_${var.environment}"
  silver_dataset    = "dpis_silver_${var.environment}"
  gold_dataset      = "dpis_gold_${var.environment}"
}

# ------------------------------------------------------------------------------
# 1. Enable Required GCP APIs
# ------------------------------------------------------------------------------
resource "google_project_service" "apis" {
  for_each = toset([
    "bigquery.googleapis.com",
    "storage.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "pubsub.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com"
  ])

  project                    = var.project_id
  service                    = each.key
  disable_on_destroy         = false
  disable_dependent_services = false
}

# ------------------------------------------------------------------------------
# 2. Cloud Storage Buckets (Source, Bronze raw, Quarantine dead-letter)
# ------------------------------------------------------------------------------
resource "google_storage_bucket" "source" {
  name                        = local.source_bucket
  location                    = var.dataset_location
  uniform_bucket_level_access = true
  force_destroy               = var.environment == "dev"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = var.environment == "production" ? 90 : 14
    }
  }
}

resource "google_storage_bucket" "bronze" {
  name                        = local.bronze_bucket
  location                    = var.dataset_location
  uniform_bucket_level_access = true
  force_destroy               = var.environment == "dev"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = var.environment == "production" ? 180 : 30
    }
  }
}

resource "google_storage_bucket" "quarantine" {
  name                        = local.quarantine_bucket
  location                    = var.dataset_location
  uniform_bucket_level_access = true
  force_destroy               = var.environment == "dev"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90
    }
  }
}

# ------------------------------------------------------------------------------
# 3. BigQuery Datasets
# ------------------------------------------------------------------------------
resource "google_bigquery_dataset" "control" {
  dataset_id                  = local.control_dataset
  friendly_name               = "Data Pipeline Immune System Control Plane (${var.environment})"
  description                 = "Contains registry, run metadata, incidents, remediation logs, and memory tables."
  location                    = var.dataset_location
  delete_contents_on_destroy  = var.environment == "dev"
}

resource "google_bigquery_dataset" "bronze" {
  dataset_id                  = local.bronze_dataset
  friendly_name               = "DPIS Bronze Raw Stage (${var.environment})"
  description                 = "Raw ingest tables mirrored from GCS source."
  location                    = var.dataset_location
  delete_contents_on_destroy  = var.environment == "dev"
}

resource "google_bigquery_dataset" "silver" {
  dataset_id                  = local.silver_dataset
  friendly_name               = "DPIS Silver Conformed Stage (${var.environment})"
  description                 = "Cleaned, typed, deduplicated, and validated data tables."
  location                    = var.dataset_location
  delete_contents_on_destroy  = var.environment == "dev"
}

resource "google_bigquery_dataset" "gold" {
  dataset_id                  = local.gold_dataset
  friendly_name               = "DPIS Gold Analytics Stage (${var.environment})"
  description                 = "Curated analytical marts and pipeline reliability metrics."
  location                    = var.dataset_location
  delete_contents_on_destroy  = var.environment == "dev"
}

# ------------------------------------------------------------------------------
# 4. Pub/Sub Messaging (Anomaly triggers and incident events)
# ------------------------------------------------------------------------------
resource "google_pubsub_topic" "anomalies" {
  name = "dpis-${var.environment}-anomalies"
}

resource "google_pubsub_topic" "incidents" {
  name = "dpis-${var.environment}-incidents"
}

# ------------------------------------------------------------------------------
# 5. Service Accounts (Least-Privilege Principle)
# ------------------------------------------------------------------------------
resource "google_service_account" "immune_agent_sa" {
  account_id   = "dpis-${var.environment}-agent-sa"
  display_name = "Data Pipeline Immune System Agent Service Account"
  description  = "Identity for the autonomous immune orchestrator and specialized agent tasks."
}

# Read access to data warehouse for detection, diagnosis, risk, and verification
resource "google_bigquery_dataset_iam_member" "agent_control_rw" {
  dataset_id = google_bigquery_dataset.control.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.immune_agent_sa.email}"
}

resource "google_bigquery_dataset_iam_member" "agent_silver_reader" {
  dataset_id = google_bigquery_dataset.silver.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.immune_agent_sa.email}"
}

# Read access to quarantine and bronze buckets
resource "google_storage_bucket_iam_member" "agent_quarantine_rw" {
  bucket = google_storage_bucket.quarantine.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.immune_agent_sa.email}"
}

# ------------------------------------------------------------------------------
# 6. Secret Manager (SLAs, Webhooks, API Credentials)
# ------------------------------------------------------------------------------
resource "google_secret_manager_secret" "slack_webhook" {
  secret_id = "dpis-${var.environment}-slack-webhook"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "slack_webhook_v1" {
  secret      = google_secret_manager_secret.slack_webhook.id
  secret_data = var.alerts_slack_webhook
}

# ------------------------------------------------------------------------------
# 7. Cloud Run Service (Immune System Controller API)
# ------------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "immune_api" {
  name     = "dpis-${var.environment}-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.immune_agent_sa.email

    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = var.cloud_run_image

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "DATASET_CONTROL"
        value = local.control_dataset
      }
    }
  }

  depends_on = [google_project_service.apis]
}
