# Gliaxin — Cursor Integration

Gives Cursor persistent memory using Gliaxin's local API.

## Setup

### 1. Start Gliaxin

```bash
cd oss
cp .env.example .env
docker compose up -d
cd backend && npm run db:migrate
```

### 2. Install

```bash
curl -fsSL https://gliaxin.com/cursor.sh | sh
```

### 3. Set environment variables

```bash
export GLIAXIN_API_KEY="your-secret-api-key-here"
export GLIAXIN_API_URL="http://localhost:9823"
export GLIAXIN_USER_ID="$(whoami)"
```

## Option A — .cursorrules (simplest)

Copy `.cursorrules` to your project root:

```bash
cp ~/.gliaxin/cursor/.cursorrules .cursorrules
```

This instructs Cursor to call the Gliaxin search API before generating responses and include results as context.

## Option B — MCP Server (recommended)

Add to your Cursor MCP config (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "gliaxin": {
      "command": "python3",
      "args": ["~/.gliaxin/cursor/mcp_server.py"],
      "env": {
        "GLIAXIN_API_KEY": "<your-key>",
        "GLIAXIN_API_URL": "http://localhost:9823",
        "GLIAXIN_USER_ID": "<your-username>"
      }
    }
  }
}
```

The MCP server exposes two tools Cursor can call natively:
- `memory_search` — search past memories
- `memory_add` — save a turn

## Files

| File | Purpose |
|---|---|
| `.cursorrules` | Project-scoped rules file (Option A) |
| `mcp_server.py` | MCP server exposing memory tools (Option B) |
| `skill.md` | Cursor skill definition |
| `install.sh` | One-command installer |

## Troubleshooting

**MCP server not showing up in Cursor**

Check that `~/.cursor/mcp.json` has the `gliaxin` entry and that the path to `mcp_server.py` is absolute. Then restart Cursor — MCP servers are loaded on startup.

Test the server manually:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 ~/.gliaxin/cursor/mcp_server.py
```
You should get back a JSON response listing `memory_search` and `memory_add`.

**MCP server connects but search returns nothing**

The server reaches out to `GLIAXIN_API_URL`. Make sure Gliaxin is running:
```bash
curl http://localhost:9823/health
```
If that fails — start Gliaxin with `docker compose up -d` from the `oss/` folder.

**`.cursorrules` not being picked up**

The file must be in the project root (same folder you opened in Cursor). Cursor reads it on project open — reopen the folder after adding it.
