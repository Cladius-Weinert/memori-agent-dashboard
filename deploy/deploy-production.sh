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
  echo "⚠️  Edit $ENV_FILE — set JWT_SECRET, DATABASE_URL, and LLM_API_KEY before production use."
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
  COMPOSE="docker compose -f docker-compose.yml"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose -f docker-compose.yml"
else
  echo "ERROR: docker compose not installed. Run: sudo apt install docker-compose-v2"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  COMPOSE="sudo $COMPOSE"
fi

DATABASE_URL="$(grep '^DATABASE_URL=' "$ENV_FILE" | cut -d= -f2- || true)"
SUPABASE_REF="$(grep '^SUPABASE_PROJECT_REF=' "$ENV_FILE" | cut -d= -f2- || true)"

if echo "$DATABASE_URL" | grep -qi supabase || [[ -n "$SUPABASE_REF" ]]; then
  echo "✅ Using Supabase Postgres (schema: ${DB_SCHEMA:-agent})"
  if ! grep -q '^API_NETWORK_MODE=' "$ENV_FILE" 2>/dev/null; then
    echo "API_NETWORK_MODE=host" >> "$ENV_FILE"
    echo "API_INTERNAL_URL=http://host.docker.internal:8000" >> "$ENV_FILE"
  fi
  export API_NETWORK_MODE=host
  export API_INTERNAL_URL=http://host.docker.internal:8000
  $COMPOSE up -d --build redis api web
else
  detect_db_url() {
    local internal="postgresql+asyncpg://memori:memori@host.docker.internal:5433/memori?ssl=disable"
    $COMPOSE --profile local-db up -d --build db redis
    sleep 3
    if $COMPOSE run --rm --no-deps -T api python3 -c \
      "import socket; s=socket.create_connection(('host.docker.internal',5433),2); s.close()" 2>/dev/null; then
      echo "$internal"
    else
      echo "postgresql+asyncpg://memori:memori@db:5432/memori?ssl=disable"
    fi
  }

  DETECTED_DB_URL="$(detect_db_url)"
  if grep -q '^DATABASE_URL=' "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${DETECTED_DB_URL}|" "$ENV_FILE"
  else
    echo "DATABASE_URL=${DETECTED_DB_URL}" >> "$ENV_FILE"
  fi
  $COMPOSE up -d --build api web
fi

echo ""
echo "=== Deployed ==="
echo "  Web IDE:  http://localhost:3002/ide"
echo "  API:      http://localhost:9001/docs"
echo "  Health:   http://localhost:9001/healthz"
echo ""
echo "Logs: cd deploy && docker compose logs -f api web"
