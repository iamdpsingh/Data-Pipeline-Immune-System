# Cloud Storage Lakehouse Buckets Module
resource "google_storage_bucket" "buckets" {
  for_each      = toset(var.bucket_prefixes)
  name          = "${each.value}-${var.environment}-${var.project_id}"
  location      = var.location
  project       = var.project_id
  force_destroy = false
  uniform_bucket_level_access = true
}
