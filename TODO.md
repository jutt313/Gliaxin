# Gliaxin OSS — Build Checklist

Status legend: [ ] todo  [x] done  [-] skip/not needed

---

## Step 1 — Stripped Backend (Personal Mode)

- [x] oss/backend/src/main.py — no Firebase, no billing, no dashboard routes
- [x] oss/backend/src/auth.py — static OSS_API_KEY from env (no Firebase)
- [x] oss/backend/src/api_key_auth.py — env-based key check, returns fixed project_id
- [x] oss/backend/src/bootstrap.py — seeds Project + Vault on startup if missing
- [x] oss/backend/src/database.py — same pool logic, stripped billing enums
- [x] oss/backend/src/notify.py — no-op (no notifications in OSS)
- [x] oss/backend/src/logger.py — copied unchanged
- [x] oss/backend/src/metrics.py — copied unchanged
- [x] oss/backend/src/key_hashing.py — copied unchanged
- [x] oss/backend/src/routes/agents.py — stripped (no rate_limit, no notify, no firebase)
- [x] oss/backend/src/routes/memory.py — stripped (no rate_limit, uses verify_api_key)

## Step 2 — Provider Abstraction Layer

- [x] oss/backend/src/providers/__init__.py — factory: get_provider() based on ACTIVE_LLM_PROVIDER
- [x] oss/backend/src/providers/base.py — abstract interface: generate_json, generate_text, embed, generate_turn_json
- [x] oss/backend/src/providers/gemini.py — Gemini impl with tool-calling loop
- [x] oss/backend/src/providers/openai_provider.py — OpenAI impl (json mode + 768-dim embeddings)
- [x] oss/backend/src/providers/claude.py — Anthropic Claude impl (needs OpenAI for embeddings)
- [x] oss/backend/src/providers/kimi.py — Kimi impl (OpenAI-compatible)
- [x] oss/backend/src/worker.py — refactored to use provider abstraction

## Step 3 — Database Setup

- [x] oss/backend/database/schema.prisma — stripped (no User/Billing/ApiKey/Notification/UsageMetric)
- [x] oss/backend/package.json — Prisma scripts
- [x] oss/backend/prisma.config.ts — same as original
- [x] oss/docker-compose.yml — Postgres + pgvector, one-command startup
- [ ] Verify migrations work clean on a fresh DB (manual test needed)

## Step 4 — Environment

- [x] oss/.env.example — all env vars with comments per section
- [x] oss/backend/requirements.txt — no firebase-admin
- [x] oss/backend/Dockerfile — same as original

## Step 5 — Agent Integrations

- [x] oss/integrations/claude-code/fetch_memory.py
- [x] oss/integrations/claude-code/save_memory.py
- [x] oss/integrations/claude-code/tool_memory.py
- [x] oss/integrations/claude-code/README.md
- [x] oss/integrations/codex/common.py
- [x] oss/integrations/codex/fetch_memory.py
- [x] oss/integrations/codex/save_memory.py
- [x] oss/integrations/codex/tool_memory.py
- [x] oss/integrations/codex/README.md
- [x] oss/integrations/cursor/README.md
- [x] oss/integrations/copilot/README.md

## Step 6 — Docs

- [x] oss/README.md — quickstart, provider setup, agent integration guide

---

## Build Order (Suggested)

1. [x] Step 2 — Provider abstraction (unblocks everything)
2. [x] Step 1 — Stripped backend (uses providers)
3. [x] Step 3 — DB + Docker setup
4. [x] Step 4 — Env file
5. [x] Step 5 — Agent integrations
6. [x] Step 6 — Docs

---

## Known TODOs After First Release

- [ ] Add Cursor MCP server integration (proper config file)
- [ ] Add Copilot extension integration
- [ ] Python SDK wrapper signature alignment (client.py vs wrap.py mismatch from original)
- [ ] Add smoke test script for local install verification
- [ ] Add one-line install scripts per agent
- [ ] OpenClaw integration
