# Vultr VPS provisioner
terraform {
  required_providers {
    vultr = { source = "vultr/vultr", version = "~> 2.0" }
  }
}

variable "api_key"     { type = string }
variable "region"      { default = "ewr" }
variable "plan"        { default = "vc2-1c-1gb" }
variable "os_id"       { default = 1742 }
variable "label"       { default = "memori-node" }
variable "ssh_key_id"  { type = string }

provider "vultr" { api_key = var.api_key }

resource "vultr_instance" "this" {
  region     = var.region
  plan       = var.plan
  os_id      = var.os_id
  label      = var.label
  ssh_key_id = var.ssh_key_id
}

output "instance_id" { value = vultr_instance.this.id }
output "main_ip"     { value = vultr_instance.this.main_ip }