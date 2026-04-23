# Gliaxin — Claude Code Integration

Gives Claude Code persistent memory across sessions using Gliaxin's local API.

## What it does

- **Before each prompt**: searches Gliaxin for relevant memories and injects them as context
- **After each response**: saves the user + assistant turn to Gliaxin memory
- **On tool writes**: blocks manual memory file creation (memory is handled by hooks)

## One-line install

```bash
curl -fsSL https://gliaxin.com/claude-code.sh | sh
```

This downloads the hooks, patches `~/.claude/settings.json`, and prints the env var setup.

---

## Manual Setup

### 1. Start Gliaxin

```bash
cd oss
cp .env.example .env
# fill in OSS_API_KEY, OSS_PROJECT_ID, and your LLM provider key
docker compose up -d
# then run migrations: cd backend && npm run db:migrate
```

### 2. Set environment variables

Add to your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
export GLIAXIN_API_KEY="your-secret-api-key-here"   # same as OSS_API_KEY in .env
export GLIAXIN_API_URL="http://localhost:9823"
export GLIAXIN_USER_ID="your-username"               # any string
```

### 3. Add hooks to Claude Code settings

Edit `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/oss/integrations/claude-code/fetch_memory.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/oss/integrations/claude-code/save_memory.py"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/oss/integrations/claude-code/tool_memory.py"
          }
        ]
      }
    ]
  }
}
```

Replace `/path/to/oss` with the actual path.

### 4. Test it

```bash
echo '{"prompt": "what are my current projects?"}' | python3 /path/to/oss/integrations/claude-code/fetch_memory.py
```

You should see a JSON response. If memory is empty it returns `{}`.

## Files

| File | Purpose |
|---|---|
| `fetch_memory.py` | UserPromptSubmit hook — injects memory before prompt |
| `save_memory.py` | Stop hook — saves turn after response |
| `tool_memory.py` | PreToolUse hook — blocks manual memory writes |
| `skill.md` | Claude Code skill definition for Gliaxin memory |
| `install.sh` | One-line installer (auto-patches settings.json) |

## Troubleshooting

**Memory is never injected into prompts**

Run this to check if the hook can reach Gliaxin at all:
```bash
echo '{"prompt":"test"}' | GLIAXIN_API_KEY=your-key python3 ~/.claude/hooks/gliaxin_fetch_memory.py
```
If you get `connection refused` — Gliaxin isn't running. Start it with `docker compose up -d` from the `oss/` folder.
If you get `401 Unauthorized` — `GLIAXIN_API_KEY` doesn't match `OSS_API_KEY` in your `.env`.

**Turns are being fetched but nothing is saved / search returns nothing**

Memory extraction runs in the background worker. Give it 5–10 seconds after a turn before searching. Check worker logs:
```bash
docker compose logs api --tail=30
```
If you see `RuntimeError: no provider configured` — your `ACTIVE_LLM_PROVIDER` env var is set but the matching API key is missing from `.env`.

**Hook fires but Claude Code ignores the output**

Claude Code only injects hook output if it's valid JSON with a `prompt` key. Test the output format:
```bash
echo '{"prompt":"what did I work on yesterday?"}' | python3 ~/.claude/hooks/gliaxin_fetch_memory.py
```
Output should be a JSON object. If it's plain text or empty, the hook is failing silently — check that `GLIAXIN_API_KEY` and `GLIAXIN_USER_ID` are exported in your shell.

**Hook not firing at all**

Open `~/.claude/settings.json` and confirm the hook entries are there. Then restart Claude Code — settings are loaded on startup.
