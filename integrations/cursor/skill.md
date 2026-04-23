# Gliaxin Memory — Cursor Skill

You have access to a persistent memory system called Gliaxin that stores facts from your AI coding sessions.

## What memory is for

- Recalling user preferences and past decisions across sessions
- Surfacing relevant project context before answering
- Avoiding redundant questions

## How it works in Cursor

Cursor does not have native pre/post-prompt hooks. Gliaxin integrates via one of two paths:

### Option A — .cursorrules (always active)

A `.cursorrules` file in the project root instructs Cursor to call the Gliaxin search API before answering. Memory is fetched inline and injected as context.

### Option B — MCP Server (recommended)

A local MCP server exposes `memory_search` and `memory_add` as Cursor tools. Cursor calls them automatically when the task benefits from memory.

## If memory is injected

When you see:

```
--- Gliaxin Memory ---
[retrieved memories]
--- End Memory ---
```

Treat this as authoritative history about the user's preferences and past decisions.

## Env vars required

- `GLIAXIN_API_KEY` — your OSS_API_KEY value
- `GLIAXIN_API_URL` — defaults to `http://localhost:9823`
- `GLIAXIN_USER_ID` — identifies the user (e.g. your username)
