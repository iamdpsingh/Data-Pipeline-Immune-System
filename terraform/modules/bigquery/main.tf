# BigQuery Datasets & Partitioned Tables Module
resource "google_bigquery_dataset" "datasets" {
  for_each   = toset(var.dataset_names)
  dataset_id = "${each.value}_${var.environment}"
  location   = var.location
  project    = var.project_id
}
