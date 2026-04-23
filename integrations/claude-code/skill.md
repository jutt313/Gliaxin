# Gliaxin Memory — Claude Code Skill

You have access to a persistent memory system called Gliaxin. It stores facts from your conversations and makes them searchable across sessions.

## What memory is for

- Remembering decisions, preferences, and patterns specific to this user and project
- Avoiding asking the same questions twice
- Surfacing relevant past context before answering

## How it works automatically

Memory is wired into Claude Code hooks:
- **Before each prompt** (`UserPromptSubmit`): relevant memories are injected as context
- **After each reply** (`Stop`): the turn is sent to Gliaxin for extraction
- **Tool use**: `PreToolUse` blocks attempts to write memory files manually

You do not need to call Gliaxin manually. The hooks handle it.

## If memory is injected

When you see a block like:

```
--- Gliaxin Memory ---
[memory content]
--- End Memory ---
```

That is retrieved context from past sessions. Treat it as ground truth about this user's preferences and history.

## Env vars required

- `GLIAXIN_API_KEY` — your OSS_API_KEY value
- `GLIAXIN_API_URL` — defaults to `http://localhost:9823`
- `GLIAXIN_USER_ID` — identifies the user (e.g. your username)
