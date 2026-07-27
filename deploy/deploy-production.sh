#!/usr/bin/env bash
# Opsora Agent — production deploy via Docker Compose
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$ROOT/deploy"
ENV_FILE="$DEPLOY_DIR/.env"

echo "=== Opsora Agent Production Deploy ==="

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Creating $ENV_FILE from example..."
  cp "$DEPLOY_DIR/.env.example" "$ENV_FILE"
  echo "⚠️  Edit $ENV_FILE — set JWT_SECRET and LLM_API_KEY before production use."
fi

# Inject NVIDIA key if available in environment
if [[ -n "${NGC_CLI_API_KEY:-}" && -n "${LLM_API_KEY:-}" ]]; then
  :
elif [[ -n "${NGC_CLI_API_KEY:-}" ]]; then
  if grep -q '^LLM_API_KEY=your-nvidia' "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^LLM_API_KEY=.*|LLM_API_KEY=${NGC_CLI_API_KEY}|" "$ENV_FILE"
    echo "✅ Injected NGC_CLI_API_KEY into LLM_API_KEY"
  fi
elif [[ -n "${NVIDIA_API_KEY:-}" ]]; then
  if grep -q '^LLM_API_KEY=your-nvidia' "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^LLM_API_KEY=.*|LLM_API_KEY=${NVIDIA_API_KEY}|" "$ENV_FILE"
    echo "✅ Injected NVIDIA_API_KEY into LLM_API_KEY"
  fi
fi

# Strong JWT if still default
if grep -q 'change-me-in-production' "$ENV_FILE" 2>/dev/null; then
  JWT=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p)
  sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${JWT}|" "$ENV_FILE"
  echo "✅ Generated random JWT_SECRET"
fi

cd "$DEPLOY_DIR"
echo "Building and starting containers..."
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "ERROR: docker compose not installed. Run: sudo apt install docker-compose-v2"
  exit 1
fi

# Use sudo if docker socket not accessible
if ! docker info >/dev/null 2>&1; then
  COMPOSE="sudo $COMPOSE"
fi

$COMPOSE up -d --build

echo ""
echo "=== Deployed ==="
echo "  Web IDE:  http://localhost:3002/ide"
echo "  API:      http://localhost:9001/docs"
echo "  Health:   http://localhost:9001/healthz"
echo ""
echo "Logs: cd deploy && docker compose logs -f api web"
