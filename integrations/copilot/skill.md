# Gliaxin Memory — GitHub Copilot Skill

You have access to a persistent memory system called Gliaxin. It stores facts from your AI coding sessions and makes them available across sessions.

## What memory is for

- Remembering user preferences, patterns, and past decisions
- Carrying project context across VS Code sessions
- Reducing repeated questions

## How it works in Copilot

GitHub Copilot does not have native pre/post-prompt hooks (as of 2025). Gliaxin integrates via:

- **copilot-instructions.md** — a repo-scoped instruction file that tells Copilot how to use Gliaxin memory
- **VS Code Tasks** — a task that fetches memory and writes it to `.gliaxin-context.txt` before each session
- **VS Code Extension** (coming soon) — a proper Copilot Extension for native memory search/add

## If memory is available

Include the contents of `.gliaxin-context.txt` (if it exists in the workspace root) as context when generating responses.

## Env vars required

- `GLIAXIN_API_KEY` — your OSS_API_KEY value
- `GLIAXIN_API_URL` — defaults to `http://localhost:9823`
- `GLIAXIN_USER_ID` — identifies the user (e.g. your username)
