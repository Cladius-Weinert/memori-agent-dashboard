# AWS EC2 provisioner
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

variable "region" { default = "us-east-1" }
variable "instance_type" { default = "t3.medium" }
variable "name" { default = "memori-node" }
variable "key_name" { type = string }
variable "vpc_id" { default = null }
variable "allowed_cidr" { default = "0.0.0.0/0" }
variable "ami" { default = null }

data "aws_ami" "ubuntu" {
  most_recent = true
  filter { name = "name" values = ["ubuntu/images/hvm-ssd/ubuntu-22.04-*-server-*"] }
  filter { name = "virtualization-type" values = ["hvm"] }
  owners = ["099720109477"]
}

locals {
  ami_id = var.ami != null ? var.ami : data.aws_ami.ubuntu.id
}

provider "aws" { region = var.region }

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter { name = "vpc-id" values = [var.vpc_id != null ? var.vpc_id : data.aws_vpc.default.id] }
}

resource "aws_security_group" "memori" {
  name        = "memori-${var.name}"
  description = "Memori managed SG"
  vpc_id      = var.vpc_id != null ? var.vpc_id : data.aws_vpc.default.id

  ingress { from_port = 22 to_port = 22 protocol = "tcp" cidr_blocks = [var.allowed_cidr] }
  ingress { from_port = 80 to_port = 80 protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  ingress { from_port = 443 to_port = 443 protocol = "tcp" cidr_blocks = ["0.0.0.0/0"] }
  ingress { from_port = 9100 to_port = 9100 protocol = "tcp" cidr_blocks = [var.allowed_cidr] }
  egress { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }

  tags = { Name = "memori-${var.name}", ManagedBy = "memori" }
}

data "aws_subnet" "target" {
  id = data.aws_subnets.default.ids[0]
}

resource "aws_instance" "this" {
  ami                    = local.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  subnet_id              = data.aws_subnet.target.id
  vpc_security_group_ids = [aws_security_group.memori.id]
  associate_public_ip_address = true

  tags = {
    Name      = var.name
    ManagedBy = "memori"
  }
}

output "instance_id" { value = aws_instance.this.id }
output "public_ip"  { value = aws_instance.this.public_ip }