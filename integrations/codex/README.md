# Gliaxin — Codex Integration

Gives OpenAI Codex persistent memory using Gliaxin's local API.

## One-line install

```bash
curl -fsSL https://gliaxin.com/codex.sh | sh
```

This downloads the hooks, patches `~/.codex/config.json`, and prints the env var setup.

---

## Manual Setup

### 1. Start Gliaxin (same as Claude Code integration)

```bash
cd oss
cp .env.example .env
docker compose up -d
cd backend && npm run db:migrate
```

### 2. Set environment variables

```bash
export GLIAXIN_API_KEY="your-secret-api-key-here"
export GLIAXIN_API_URL="http://localhost:9823"
export GLIAXIN_USER_ID="your-username"
```

### 3. Wire up hooks in Codex

Add to your `.codex/hooks.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": "/path/to/oss/integrations/codex/fetch_memory.py",
    "Stop": "/path/to/oss/integrations/codex/save_memory.py"
  }
}
```

## Files

| File | Purpose |
|---|---|
| `common.py` | Shared HTTP helpers |
| `fetch_memory.py` | UserPromptSubmit hook — injects memory before prompt |
| `save_memory.py` | Stop hook — saves turn after response |
| `tool_memory.py` | Optional PreToolUse hook |
| `skill.md` | Codex skill definition for Gliaxin memory |
| `install.sh` | One-line installer (auto-patches config.json) |

## Test

```bash
echo '{"prompt": "test query"}' | python3 /path/to/oss/integrations/codex/fetch_memory.py
```

## Troubleshooting

**No memory injected before prompts**

Test the hook directly:
```bash
echo '{"prompt":"test"}' | GLIAXIN_API_KEY=your-key python3 ~/.codex/hooks/gliaxin_fetch_memory.py
```
`connection refused` → Gliaxin isn't running, start with `docker compose up -d`.
`401` → `GLIAXIN_API_KEY` doesn't match `OSS_API_KEY` in `.env`.

**Memory is fetched but nothing is ever extracted**

Extraction runs async in the background. Wait ~10 seconds then check:
```bash
docker compose logs api --tail=30
```
Look for `worker` log lines. If you see an API key error for your LLM provider, that key is missing or wrong in `.env`.

**Hook not running**

Check that `~/.codex/config.json` has the hook entries — the install script writes them there. If you edited `config.json` manually, make sure the paths are absolute (not relative). Restart Codex after any config change.
