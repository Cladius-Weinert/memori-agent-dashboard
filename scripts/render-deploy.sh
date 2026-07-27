#!/usr/bin/env bash
# Create Opsora stack on Render via API. Requires billing + RENDER_API_KEY.
set -euo pipefail

: "${RENDER_API_KEY:?Set RENDER_API_KEY}"
OWNER="${RENDER_OWNER_ID:-tea-d8pa0emgvqtc738vi4t0}"
API="https://api.render.com/v1"
HDR=(-H "Authorization: Bearer $RENDER_API_KEY" -H "Content-Type: application/json")

post() {
  local path="$1" body="$2"
  curl -sf -X POST "$API$path" "${HDR[@]}" -d "$body"
}

echo "==> Creating Postgres opsora-db"
PG=$(post /postgres "{
  \"name\": \"opsora-db\",
  \"ownerId\": \"$OWNER\",
  \"region\": \"singapore\",
  \"plan\": \"basic_256mb\",
  \"databaseName\": \"memori\",
  \"databaseUser\": \"memori\",
  \"version\": \"16\"
}") || { echo "Postgres failed — check billing at dashboard.render.com/billing"; exit 1; }
PG_ID=$(echo "$PG" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Postgres ID: $PG_ID"

echo "==> Creating Redis opsora-redis"
RD=$(post /redis "{
  \"name\": \"opsora-redis\",
  \"ownerId\": \"$OWNER\",
  \"region\": \"singapore\",
  \"plan\": \"starter\",
  \"maxmemoryPolicy\": \"allkeys_lru\"
}")
RD_ID=$(echo "$RD" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Redis ID: $RD_ID"

echo "==> Creating Web Service opsora-api"
SVC=$(post /services "{
  \"type\": \"web_service\",
  \"name\": \"opsora-api\",
  \"ownerId\": \"$OWNER\",
  \"repo\": \"https://github.com/Cladius-Weinert/memori-agent-dashboard\",
  \"branch\": \"cursor/full-stack-setup-64c1\",
  \"autoDeploy\": \"yes\",
  \"serviceDetails\": {
    \"runtime\": \"docker\",
    \"plan\": \"starter\",
    \"region\": \"singapore\",
    \"envSpecificDetails\": {
      \"dockerfilePath\": \"deploy/Dockerfile.api\",
      \"dockerContext\": \".\"
    },
    \"healthCheckPath\": \"/healthz\"
  }
}")
SVC_ID=$(echo "$SVC" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('service',d).get('id', d.get('id','')))")
echo "Service ID: $SVC_ID"

echo "==> Waiting for Postgres connection info..."
for _ in $(seq 1 30); do
  INFO=$(curl -sf "${HDR[@]}" "$API/postgres/$PG_ID/connection-info" 2>/dev/null || true)
  if echo "$INFO" | rg -q 'connectionString'; then break; fi
  sleep 10
done

CONN=$(echo "$INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('connectionString',''))")
if [ -z "$CONN" ]; then echo "Could not get DB connection string yet"; exit 1; fi
DB_URL=$(python3 -c "u='$CONN'; print(u.replace('postgresql://','postgresql+asyncpg://',1))")

# Load secrets from local .env if present
ENV_FILE="/agent/repos/memori-agent-dashboard/apps/api/.env"
JWT_SECRET=$(rg '^JWT_SECRET=' "$ENV_FILE" | cut -d= -f2- || openssl rand -hex 32)
LLM_KEY=$(rg '^LLM_API_KEY=' "$ENV_FILE" | cut -d= -f2- || true)
NVIDIA_KEY=$(rg '^NVIDIA_API_KEY=' "$ENV_FILE" | cut -d= -f2- || true)
GH_TOKEN=$(rg '^GITHUB_TOKEN=' "$ENV_FILE" | cut -d= -f2- || true)

echo "==> Setting environment variables"
curl -sf -X PUT "$API/services/$SVC_ID/env-vars" "${HDR[@]}" -d "$(python3 <<PY
import json, os
vars = [
  {"key":"DATABASE_URL","value":"$DB_URL"},
  {"key":"REDIS_URL","value":"redis://placeholder:6379/0"},
  {"key":"JWT_SECRET","value":"$JWT_SECRET"},
  {"key":"JWT_ALGORITHM","value":"HS256"},
  {"key":"ACCESS_TOKEN_EXPIRE_MINUTES","value":"43200"},
  {"key":"MOBILE_ACCESS_TOKEN_EXPIRE_DAYS","value":"90"},
  {"key":"LLM_BASE_URL","value":"https://integrate.api.nvidia.com/v1"},
  {"key":"LLM_MODEL","value":"meta/llama-3.1-70b-instruct"},
  {"key":"CORS_ORIGINS","value":"*"},
  {"key":"OPSORA_PERMANENT_GATEWAY","value":"https://mwbgkkthwwlcndccnbnf.supabase.co/functions/v1/opsora-api"},
]
for k in ("LLM_API_KEY","NVIDIA_API_KEY","GITHUB_TOKEN"):
    v = os.environ.get(k.replace("LLM_API_KEY","LLM_KEY").replace("NVIDIA_API_KEY","NVIDIA_KEY").replace("GITHUB_TOKEN","GH_TOKEN"), "")
    if k == "LLM_API_KEY": v = "$LLM_KEY"
    if k == "NVIDIA_API_KEY": v = "$NVIDIA_KEY"
    if k == "GITHUB_TOKEN": v = "$GH_TOKEN"
    if v: vars.append({"key":k,"value":v})
print(json.dumps(vars))
PY
)" >/dev/null

URL=$(echo "$SVC" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('service',d); print(s.get('serviceDetails',{}).get('url',''))")
echo "Deploy triggered. Service URL: ${URL:-https://opsora-api.onrender.com}"
echo "Update Supabase mobile_api_url after health check passes."
