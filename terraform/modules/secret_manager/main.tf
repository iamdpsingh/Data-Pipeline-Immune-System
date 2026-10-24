# Google Cloud Secret Manager Module
resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(var.secret_names)
  secret_id = "dpis-${var.environment}-${each.value}"
  project   = var.project_id
  replication {
    auto {}
  }
}
