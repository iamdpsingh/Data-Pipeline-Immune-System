variable "project_id" { type = string }
variable "environment" { type = string }
variable "location" { type = string, default = "us-central1" }
variable "bucket_prefixes" { type = list(string), default = ["dpis-source", "dpis-bronze", "dpis-silver", "dpis-gold", "dpis-quarantine"] }
