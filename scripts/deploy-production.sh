#!/usr/bin/env bash
# Production deploy helper — Docker API + Supabase gateway sync
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="$ROOT/deploy"
SUPABASE_PROJECT="mwbgkkthwwlcndccnbnf"
GATEWAY_URL="https://${SUPABASE_PROJECT}.supabase.co/functions/v1/opsora-api"

echo "==> Starting production stack (Docker)"
cd "$DEPLOY_DIR"
docker compose up -d db redis api

echo "==> Waiting for API health"
for _ in $(seq 1 30); do
  if curl -sf --max-time 3 http://localhost:9001/healthz >/dev/null 2>&1; then
    echo "API ready on http://localhost:9001"
    break
  fi
  sleep 2
done

BACKEND_URL="${OPSORA_BACKEND_URL:-}"
if [ -z "$BACKEND_URL" ]; then
  echo "==> Set OPSORA_BACKEND_URL to your permanent URL (e.g. https://opsora-api.onrender.com)"
  echo "    For tunnel mode, run: bash /agent/repos/opsora/scripts/keepalive.sh"
  exit 0
fi

if [ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
  echo "==> Syncing backend to Supabase: $BACKEND_URL"
  PAYLOAD=$(python3 - <<PY
import json
print(json.dumps({
  "url": "$BACKEND_URL",
  "backend_url": "$BACKEND_URL",
  "gateway_url": "$GATEWAY_URL",
  "endpoints": ["$BACKEND_URL"],
  "version": "1.6.8",
  "region": "ap-southeast-1",
}))
PY
)
  curl -sf -X PATCH \
    "https://${SUPABASE_PROJECT}.supabase.co/rest/v1/system_config?key=eq.mobile_api_url" \
    -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
    -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=minimal" \
    -d "{\"value\": $PAYLOAD}"
  echo ""
fi

echo "==> Gateway: $GATEWAY_URL"
curl -sf "$GATEWAY_URL/healthz" && echo ""
echo "Deploy sync complete."
