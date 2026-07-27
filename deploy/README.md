# Deploy — Opsora Agent IDE

## Quick Production (Docker Compose)

```bash
cd memori-agent-dashboard
bash deploy/deploy-production.sh
# Web IDE: http://localhost:3002/ide
# API docs: http://localhost:9001/docs
```

The script auto-detects Docker DB networking. If the API container cannot reach `db:5432` (common on some cloud VMs), it routes via `host.docker.internal:5433` instead.

Copy and edit secrets first:

```bash
cp deploy/.env.example deploy/.env
# Set JWT_SECRET, LLM_API_KEY (NVIDIA Integrate API key)
```

## Local Development (docker-compose)

```bash
# 1) Clone repo
cd memori-agent-dashboard

# 2) Copy env
cp deploy/.env.example .env
# Edit JWT_SECRET, LLM_API_KEY, etc.

# 3) Start everything
docker compose -f deploy/docker-compose.yml up -d

# 4) Open
#   Dashboard: http://localhost:3000
#   API:       http://localhost:8000
#   Docs:      http://localhost:8000/docs
#   Prometheus: http://localhost:9090
#   Grafana:   http://localhost:3001 (admin/admin)
```

To include monitoring (`docker compose up prometheus grafana`):

```bash
docker compose -f deploy/docker-compose.yml --profile monitoring up -d
```

## Fly.io Deployment

```bash
# 1) Install flyctl & login
curl -fsSL https://fly.io/install.sh | sh
fly auth login

# 2) Launch
fly launch --dockerfile deploy/Dockerfile.api --name memori-agent-api
fly launch --dockerfile deploy/Dockerfile.web --name memori-agent-web

# 3) Set secrets
fly secrets set JWT_SECRET=<random> LLM_API_KEY=<key> DATABASE_URL=<from-fly-postgres>

# 4) Deploy
fly deploy --dockerfile deploy/Dockerfile.api
fly deploy --dockerfile deploy/Dockerfile.web
```

## Railway Deployment

1. Push to GitHub
2. Connect repo to Railway
3. Set env vars from `deploy/.env.example`
4. Railway auto-detects `deploy/railway.json`

## Render Deployment

1. Push to GitHub
2. Connect repo to Render as a "Blueprint"
3. Render auto-detects `deploy/render.yaml`
4. Fill in env vars when prompted
5. Authenticate Render MCP in Cursor (`list_workspaces`) for agent-assisted deploy

## VPS Production (98.94.100.100 / sslip.io)

**Preferred** when you have SSH access to `opsora-brain` EC2:

```bash
# On VPS (ubuntu@98.94.100.100)
git clone https://github.com/Cladius-Weinert/memori-agent-dashboard.git
cd memori-agent-dashboard
cp deploy/.env.example deploy/.env
# Edit: LLM_API_KEY, CORS_ORIGINS for agent.98-94-100-100.sslip.io
bash deploy/deploy-production.sh
```

Expose via Caddy/nginx:
- `agent.98-94-100-100.sslip.io` → `localhost:3002` (web)
- API reverse-proxy → `localhost:9001`

Or use GitHub Actions (set repo secrets `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`):

```yaml
# .github/workflows/deploy-vps.yml — see repo
```

## External Database (Supabase fallback)

If Docker Postgres is unreliable, point `DATABASE_URL` at Supabase Postgres (project `opsora-prod`):

```
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?ssl=require
```

Run migrations once: `cd apps/api && alembic upgrade head`

## Terraform Provisioning

```bash
# Prerequisites: terraform binary + cloud provider credentials

# Set terraform vars and provision
cd packages/terraform-templates/scripts
bash bootstrap.sh --provider aws --name "my-node"

# Providers supported: aws | gcp | digitalocean | vultr
```

## Monitoring

- **Prometheus** auto-scrapes API metrics (port 8000) and Node Exporter (port 9100)
- **Grafana** dashboards connect to Prometheus datasource
- Node Exporter must be installed on target instances (included in `cloud-init/memori-agent-node.yaml`)