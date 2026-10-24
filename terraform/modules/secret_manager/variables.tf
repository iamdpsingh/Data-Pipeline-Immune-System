variable "project_id" { type = string }
variable "environment" { type = string }
variable "secret_names" { type = list(string), default = ["smtp-credentials", "whatsapp-token", "telegram-token"] }
