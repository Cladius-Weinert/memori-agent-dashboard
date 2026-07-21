# Deploy — Memori Agent & Dashboard

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