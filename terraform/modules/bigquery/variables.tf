variable "project_id" { type = string }
variable "environment" { type = string }
variable "location" { type = string, default = "us-central1" }
variable "dataset_names" { type = list(string), default = ["dpis", "dpis_bronze", "dpis_silver", "dpis_gold", "dpis_audit"] }
