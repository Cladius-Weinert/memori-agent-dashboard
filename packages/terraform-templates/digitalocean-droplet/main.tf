# DigitalOcean Droplet provisioner
terraform {
  required_providers {
    digitalocean = { source = "digitalocean/digitalocean", version = "~> 2.0" }
  }
}

variable "do_token"   { type = string }
variable "region"      { default = "nyc3" }
variable "size"        { default = "s-1vcpu-1gb" }
variable "image"       { default = "ubuntu-22-04-x64" }
variable "name"        { default = "memori-node" }
variable "ssh_key_id"  { type = string }

provider "digitalocean" {
  token = var.do_token
}

resource "digitalocean_droplet" "this" {
  name     = var.name
  region   = var.region
  size     = var.size
  image    = var.image
  ssh_keys = [var.ssh_key_id]
  tags     = ["memori"]
}

output "droplet_id" { value = digitalocean_droplet.this.id }
output "ipv4"       { value = digitalocean_droplet.this.ipv4_address }