# Memori Agent & Dashboard — Frontend

Next.js 14 dashboard for managing multi-cloud infrastructure with an autonomous AI agent.

## Stack

- **Next.js 14** (App Router + TypeScript)
- **Tailwind CSS** (dark theme, responsive)
- **SWR** (data fetching & caching)
- **Zustand** (client state w/ localStorage persistence)
- **Recharts** (CPU/RAM/Disk metric charts)
- **XTerm.js** (browser-based SSH terminal via WebSocket)
- **Lucide React** (icons)

## Pages

| Route            | Description                                  |
|------------------|----------------------------------------------|
| `/login`         | Email/password login, stores JWT             |
| `/`              | Dashboard — stats, instance cards, sparklines |
| `/instances`     | List / add / test-connection on instances     |
| `/instances/[id]`| Detail with Terminal / Logs / Metrics tabs   |
| `/commands`      | Multi-target shell command runner            |
| `/agent`         | Agent chat — goal input, step timeline, approve/refuse |
| `/settings`      | Provider credentials, SSH keys, teams        |

## Setup

```bash
# 1) Install dependencies
cd apps/web
pnpm install

# 2) Copy env template
cp .env.local.example .env.local
# Edit NEXT_PUBLIC_API_URL if backend isn't on localhost:8000

# 3) Start dev server
pnpm dev
```

Open http://localhost:3000.

## Project layout

```
apps/web/
├── app/
│   ├── page.tsx            # Root route → Dashboard
│   ├── layout.tsx          # Root layout → Login
│   ├── globals.css         # Tailwind base + dark theme
│   ├── api/api.ts          # Typed fetch wrappers
│   ├── hooks/useApi.ts     # SWR hooks
│   ├── stores/authStore.ts # Zustand auth state
│   ├── types/index.ts      # TypeScript interfaces
│   ├── components/Layout.tsx # Sidebar + topbar layout
│   └── pages/              # Page components
│       ├── login.tsx
│       ├── dashboard.tsx
│       ├── instances/index.tsx
│       ├── instances/[id].tsx
│       ├── commands.tsx
│       ├── agent.tsx
│       └── settings.tsx
├── components/XTermTerminal.tsx  # WebSocket xterm.js wrapper
├── next.config.js          # Proxy /api/v1 → backend
├── tailwind.config.ts
├── tsconfig.json
├── .env.local.example
└── package.json
```