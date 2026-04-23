# Gliaxin Memory — OpenClaw Skill

You have access to a persistent memory system called Gliaxin. It stores facts extracted from your conversations and makes them searchable across sessions.

## What memory is for

- Remembering user preferences, project decisions, and coding patterns
- Carrying context from past sessions into new conversations
- Avoiding repeated questions

## How it works in OpenClaw

Memory is wired into OpenClaw hooks (defined in `HOOK.md` and `handler.ts`):
- **Before each prompt**: `memory_search` is called and relevant memories are injected as context
- **After each reply**: `memory_add` is called to save the turn for future extraction

You do not call Gliaxin directly. The hook handler does it.

## If memory is injected

When you see:

```
--- Gliaxin Memory ---
[retrieved memories]
--- End Memory ---
```

This is context retrieved from past sessions. Treat it as authoritative history about the user.

## Env vars required

- `GLIAXIN_API_KEY` — your OSS_API_KEY value
- `GLIAXIN_API_URL` — defaults to `http://localhost:9823`
- `GLIAXIN_USER_ID` — identifies the user (e.g. your username)
