#!/usr/bin/env bash
# Bootstrap script — runs terraform apply for any provider
set -euo pipefail

PROVIDER=""
NAME="memori-node"

usage() {
  echo "Usage: $0 --provider {aws|gcp|digitalocean|vultr} [--name <label>]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider) PROVIDER="$2"; shift 2 ;;
    --name)     NAME="$2"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -z "$PROVIDER" ]] && usage

DIR="$(cd "$(dirname "$0")/.." && pwd)/terraform-templates/$PROVIDER"
[[ -d "$DIR" ]] || { echo "Unknown provider: $PROVIDER (no $DIR)"; exit 1; }

cd "$DIR"

case "$PROVIDER" in
  aws)
    terraform init -upgrade
    terraform apply -auto-approve \
      -var="name=$NAME" \
      -var="key_name=${AWS_KEY_NAME:-memori}" \
      -var="allowed_cidr=${ALLOWED_CIDR:-0.0.0.0/0}"
    ;;
  gcp)
    terraform init -upgrade
    terraform apply -auto-approve \
      -var="project=${GCP_PROJECT}" \
      -var="name=$NAME" \
      -var="ssh_key=${GCP_SSH_KEY}"
    ;;
  digitalocean)
    terraform init -upgrade
    terraform apply -auto-approve \
      -var="do_token=${DIGITALOCEAN_TOKEN}" \
      -var="name=$NAME" \
      -var="ssh_key_id=${DO_SSH_KEY_ID}"
    ;;
  vultr)
    terraform init -upgrade
    terraform apply -auto-approve \
      -var="api_key=${VULTR_API_KEY}" \
      -var="label=$NAME" \
      -var="ssh_key_id=${VULTR_SSH_KEY_ID}"
    ;;
esac

echo "=== DONE: $PROVIDER instance '$NAME' provisioned ==="