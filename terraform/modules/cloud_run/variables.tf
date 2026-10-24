variable "project_id" { type = string }
variable "environment" { type = string }
variable "location" { type = string, default = "us-central1" }
variable "container_image" { type = string }
variable "min_instances" { type = number, default = 0 }
variable "max_instances" { type = number, default = 5 }
