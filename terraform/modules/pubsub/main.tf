# Google Cloud Pub/Sub Module for Anomaly Telemetry
resource "google_pubsub_topic" "alerts_topic" {
  name    = "dpis-${var.environment}-alerts"
  project = var.project_id
}
