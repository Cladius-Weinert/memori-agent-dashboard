# Memori Agent & Dashboard — Backend

FastAPI backend for Memori Agent & Dashboard: a multi-cloud infrastructure management
platform with an autonomous AI agent (LangGraph + LLM safety layer) and browser-based
SSH terminals.

## Stack

- Python 3.11+
- FastAPI (async)
- SQLAlchemy 2.0 (async) + Alembic
- PostgreSQL + Redis
- asyncssh (SSH terminal + command execution pool)
- LangGraph agent runtime + OpenAI-compatible LLM client
- Celery worker for background agent jobs
- Provider adapters: AWS (boto3), GCP (google-cloud-compute), DigitalOcean, Vultr

## Project layout

```
apps/api/
├── app/
│   ├── main.py                  # FastAPI app + lifespan + routers
│   ├── core/
│   │   ├── config.py            # pydantic-settings
│   │   ├── db.py                # async engine + sessionmaker
│   │   └── security.py          # JWT + bcrypt
│   ├── models/models.py         # SQLAlchemy models
│   ├── schemas/                 # Pydantic v2 schemas
│   ├── api/v1/
│   │   ├── auth.py              # /api/v1/auth/*
│   │   ├── instances.py         # /api/v1/instances/*
│   │   ├── terminal.py          # /ws/terminal/{id}
│   │   ├── commands.py          # /api/v1/commands/*
│   │   └── agent.py             # /api/v1/agent/*
│   ├── services/
│   │   ├── ssh_pool.py          # async SSH connection pool
│   │   └── providers/           # AWS, GCP, DigitalOcean, Vultr adapters
│   ├── agent/
│   │   ├── safety.py            # denylist for destructive commands
│   │   ├── tools.py             # tool functions for the agent
│   │   └── planner.py           # LangGraph plan → execute → reflect loop
│   └── workers/
│       └── celery_app.py        # Celery worker (Redis broker)
├── alembic/
│   ├── env.py
│   └── versions/0001_initial.py # initial schema migration
├── alembic.ini
├── pyproject.toml
├── .env.example
└── README.md
```

## Setup

```bash
# 1) Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2) Install dependencies
cd apps/api
uv sync

# 3) Copy env template and edit
cp .env.example .env
# edit DATABASE_URL, REDIS_URL, JWT_SECRET, LLM_API_KEY, LLM_BASE_URL

# 4) Run database migrations
uv run alembic upgrade head

# 5) Start the API
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6) Start Celery worker (in another shell)
uv run celery -A app.workers.celery_app worker -l info
```

The API is available at http://localhost:8000 and Swagger docs at http://localhost:8000/docs.

## Endpoints (v1)

### Auth
- `POST /api/v1/auth/register` — register new user
- `POST /api/v1/auth/login` — login, returns JWT
- `GET  /api/v1/auth/me` — current user

### Instances
- `GET  /api/v1/instances` — list
- `POST /api/v1/instances` — create (body: `InstanceCreate`)
- `GET  /api/v1/instances/{id}` — read
- `POST /api/v1/instances/{id}/test-connection` — test SSH connectivity
- `POST /api/v1/instances/{id}/run-command?command=ls` — run a single command

### Terminal (WebSocket)
- `WS   /ws/terminal/{instance_id}` — bidirectional SSH terminal
  - Send: `{"type": "cmd", "data": "ls -la\n"}` or `{"type": "resize", "cols": 80, "rows": 24}`
  - Receive: `{"type": "stdout", "data": "..."}` or `{"type": "exit", "code": 0}`

### Commands
- `POST /api/v1/commands` — multi-instance command run (body: `CommandCreate`)
- `GET  /api/v1/commands/{id}` — fetch result

### Agent
- `POST /api/v1/agent/run` — start an agent job (body: `{"goal": "..."}`)
- `GET  /api/v1/agent/jobs/{id}` — fetch job status
- `GET  /api/v1/agent/jobs/{id}/stream` — SSE stream of agent steps
- `POST /api/v1/agent/actions/{id}/approve` — approve a flagged action
- `POST /api/v1/agent/actions/{id}/refuse` — refuse a flagged action

## Agent safety

The agent refuses commands matching a built-in denylist (rm -rf /, mkfs, fork bombs, etc).
Destructive commands (rm -rf, drop table, kill -9, …) are flagged as `requires_approval`
and the API exposes `/agent/actions/{id}/approve` + `/refuse` for human gating.

## Notes

- The backend expects a Postgres reachable at `DATABASE_URL` and a Redis at `REDIS_URL`.
- The LLM client uses any OpenAI-compatible endpoint. Default is NVIDIA Integrate
  (`LLM_BASE_URL=https://integrate.api.nvidia.com/v1`, `LLM_MODEL=meta/llama-3.1-70b-instruct`).
- Provider adapters (AWS/GCP/DigitalOcean) use lazy imports so missing SDKs don't crash
  import; install only what you need.
- For development without Postgres, you can swap the URL to SQLite (aiosqlite); the
  models are designed to work on both.
