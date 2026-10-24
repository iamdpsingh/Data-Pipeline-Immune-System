# Cloud Run Immune API Controller Module
resource "google_cloud_run_v2_service" "immune_api" {
  name     = "dpis-${var.environment}-api"
  location = var.location
  project  = var.project_id

  template {
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    containers {
      image = var.container_image
      resources {
        limits = { cpu = "1000m", memory = "1024Mi" }
      }
    }
  }
}
