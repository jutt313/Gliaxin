# Gliaxin OSS

Persistent memory for AI coding agents — run locally, own your data.

Gliaxin extracts durable memories from your AI agent conversations and makes them searchable across sessions. It runs entirely on your machine with no SaaS required.

## How it works

1. Your agent hook calls `POST /v1/memory/add` after each conversation turn
2. The background worker extracts facts using your chosen LLM provider
3. Memories are stored in Postgres with pgvector embeddings
4. Before each prompt, your agent hook calls `GET /v1/memory/search` to inject relevant context

## Quickstart

### 1. Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 18+ (for DB migrations via Prisma)
- An API key for at least one LLM provider (Gemini, OpenAI, Claude, or Kimi)

### 2. Configure

```bash
cd oss
cp .env.example .env
```

Edit `.env`:
- Set `OSS_API_KEY` to any secret string (e.g. `my-local-key-123`)
- Set `OSS_PROJECT_ID` to a UUID: `python3 -c "import uuid; print(uuid.uuid4())"`
- Set your LLM provider key (`GEMINI_API_KEY` / `OPENAI_API_KEY` / etc.)
- Set `ACTIVE_LLM_PROVIDER` to `gemini`, `openai`, `claude`, or `kimi`

### 3. Start the database

```bash
docker compose up -d db
```

### 4. Run migrations

```bash
cd backend
npm install
npm run db:migrate
```

### 5. Start the API

```bash
# Option A: Docker Compose (runs both DB + API)
docker compose up

# Option B: Local dev
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
npm run dev
```

The API starts on `http://localhost:9823`.

### 6. Verify

```bash
curl http://localhost:9823/health
```

### 7. Run the smoke test

```bash
GLIAXIN_API_KEY=your-key python3 smoke_test.py
```

This adds a test turn, waits for the worker to extract it, searches for it, then cleans up. All checks should print `PASS` in about 15 seconds.

## Agent Integrations

| Agent | Path | Install | Status |
|---|---|---|---|
| Claude Code | `integrations/claude-code/` | `curl -fsSL https://gliaxin.com/claude-code.sh \| sh` | Ready |
| Codex | `integrations/codex/` | `curl -fsSL https://gliaxin.com/codex.sh \| sh` | Ready |
| Cursor | `integrations/cursor/` | `curl -fsSL https://gliaxin.com/cursor.sh \| sh` | Ready (MCP + .cursorrules) |
| Copilot | `integrations/copilot/` | `curl -fsSL https://gliaxin.com/copilot.sh \| sh` | Ready |
| OpenClaw | `integrations/openclaw/` | `curl -fsSL https://gliaxin.com/openclaw.sh \| sh` | Ready |

See each folder's `README.md` for setup instructions.

## API Reference

All endpoints require `X-Api-Key: <your OSS_API_KEY>`.

### Memory

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/memory/add` | Add a turn or single message |
| `GET` | `/v1/memory/search` | Semantic + keyword search |
| `GET` | `/v1/memory/get` | Paginated list |
| `GET` | `/v1/memory/timeline` | Full history including superseded |
| `DELETE` | `/v1/memory/forget` | Delete all memory for a user |
| `GET` | `/v1/memory/conflicts` | List detected conflicts |
| `POST` | `/v1/memory/resolve` | Resolve a conflict |
| `POST` | `/v1/memory/reprocess` | Re-queue failed/done rows |

### Agents

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/agent/register` | Register/get an agent (idempotent) |
| `GET` | `/v1/agent/list` | List all agents |
| `DELETE` | `/v1/agent/{id}` | Soft-delete an agent |
| `GET` | `/v1/agent/shared` | Get project-scoped memories |

## LLM Providers

Set `ACTIVE_LLM_PROVIDER` in `.env`:

| Provider | Generation | Embeddings | Notes |
|---|---|---|---|
| `gemini` | ✅ Gemini 2.5 Flash | ✅ Native 768-dim | Default — best out of the box |
| `openai` | ✅ GPT-4o-mini | ✅ text-embedding-3-small @ 768-dim | Requires `OPENAI_API_KEY` |
| `claude` | ✅ Claude Sonnet | ⚠️ Uses OpenAI | Requires `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` |
| `kimi` | ✅ Moonshot v1 | ⚠️ Uses OpenAI | Requires `KIMI_API_KEY` + `OPENAI_API_KEY` |

## SDK

TypeScript, Python, and Go SDKs live in `sdk/`. They wrap the HTTP API.

```typescript
import { Gliaxin } from './sdk/typescript/src'
const client = new Gliaxin('your-api-key', { baseUrl: 'http://localhost:9823' })
await client.memory.add({ end_user_id: 'local', messages: [...] })
```

## Backup & Restore

All data lives in your local Postgres container. The volume is named `pgdata` and persists across restarts automatically — you only need to do this if you're moving machines or want a manual snapshot.

**Backup:**
```bash
docker exec -t $(docker compose ps -q db) pg_dump -U gliaxin gliaxin > backup.sql
```

**Restore** (on a fresh install after running migrations):
```bash
docker exec -i $(docker compose ps -q db) psql -U gliaxin gliaxin < backup.sql
```

If you're running Postgres locally (not Docker), drop the `docker exec` wrapper:
```bash
pg_dump -U gliaxin -h localhost gliaxin > backup.sql
psql -U gliaxin -h localhost gliaxin < backup.sql
```

The `backup.sql` file contains your full memory history. Keep it somewhere safe.
# Gliaxin
