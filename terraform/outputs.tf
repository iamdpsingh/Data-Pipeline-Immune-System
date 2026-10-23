# ==============================================================================
# Data Pipeline Immune System — Terraform Outputs
# ==============================================================================

output "control_dataset_id" {
  description = "The BigQuery dataset ID for the immune system control plane and audit log."
  value       = google_bigquery_dataset.control.dataset_id
}

output "bronze_dataset_id" {
  description = "The BigQuery dataset ID for bronze staging data."
  value       = google_bigquery_dataset.bronze.dataset_id
}

output "silver_dataset_id" {
  description = "The BigQuery dataset ID for validated silver data."
  value       = google_bigquery_dataset.silver.dataset_id
}

output "gold_dataset_id" {
  description = "The BigQuery dataset ID for gold aggregated analytics."
  value       = google_bigquery_dataset.gold.dataset_id
}

output "source_bucket_url" {
  description = "GCS URI for source data ingestion bucket."
  value       = google_storage_bucket.source.url
}

output "bronze_bucket_url" {
  description = "GCS URI for bronze layer bucket."
  value       = google_storage_bucket.bronze.url
}

output "quarantine_bucket_url" {
  description = "GCS URI for dead-letter quarantined data."
  value       = google_storage_bucket.quarantine.url
}

output "agent_service_account_email" {
  description = "Email of the dedicated IAM service account used by immune agents."
  value       = google_service_account.immune_agent_sa.email
}

output "cloud_run_service_uri" {
  description = "URL endpoint of the deployed Cloud Run agent controller service."
  value       = google_cloud_run_v2_service.immune_api.uri
}

output "pubsub_anomalies_topic" {
  description = "Pub/Sub topic ID for streaming anomaly alerts."
  value       = google_pubsub_topic.anomalies.id
}

output "pubsub_incidents_topic" {
  description = "Pub/Sub topic ID for incident lifecycle events."
  value       = google_pubsub_topic.incidents.id
}
