# GCP VM provisioner
terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
}

variable "project"     { type = string }
variable "region"      { default = "us-central1" }
variable "zone"        { default = "us-central1-a" }
variable "machine_type" { default = "e2-medium" }
variable "name"        { default = "memori-node" }
variable "ssh_key"     { type = string }

provider "google" {
  project = var.project
  region  = var.region
}

data "google_compute_image" "ubuntu" {
  family  = "ubuntu-2204-lts"
  project = "ubuntu-os-cloud"
}

resource "google_compute_firewall" "memori" {
  name    = "memori-${var.name}"
  network = "default"
  allow { protocol = "tcp" ports = ["22", "80", "443", "9100"] }
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["memori"]
}

resource "google_compute_instance" "this" {
  name         = var.name
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["memori"]

  boot_disk {
    initialize_params { image = data.google_compute_image.ubuntu.self_link }
  }

  network_interface {
    network = "default"
    access_config { /* ephemeral IP */ }
  }

  metadata = {
    ssh-keys = "ubuntu:${var.ssh_key}"
  }
}

output "instance_id" { value = google_compute_instance.this.instance_id }
output "public_ip"  { value = google_compute_instance.this.network_interface[0].access_config[0].nat_ip }