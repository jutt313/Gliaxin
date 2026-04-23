# Gliaxin Memory — Codex Skill

You have access to a persistent memory system called Gliaxin. It stores facts extracted from your conversations and makes them searchable across sessions.

## What memory is for

- Remembering user preferences, project decisions, and coding patterns
- Avoiding repeating questions that were already answered
- Carrying context from past sessions into new ones

## How it works automatically

Memory is wired into Codex hooks:
- **Before each prompt** (`UserPromptSubmit`): relevant memories are injected into the prompt
- **After each reply** (`Stop`): the conversation turn is sent to Gliaxin for extraction

You do not call Gliaxin directly. The hooks handle it.

## If memory is injected

When you see a block like:

```
--- Gliaxin Memory ---
[memory content]
--- End Memory ---
```

This is context retrieved from past sessions. Treat it as authoritative history about this user.

## Env vars required

- `GLIAXIN_API_KEY` — your OSS_API_KEY value
- `GLIAXIN_API_URL` — defaults to `http://localhost:9823`
- `GLIAXIN_USER_ID` — identifies the user (e.g. your username)
