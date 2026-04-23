# Copilot Instructions — Gliaxin Memory

This project uses Gliaxin for persistent memory across sessions.

## Before answering

If `.gliaxin-context.txt` exists in the workspace root, read it and use its contents as context for this session. It contains memories retrieved from past sessions relevant to the current task.

## How to fetch memory manually

Run the VS Code task "Fetch Gliaxin Memory" (defined in `.vscode/tasks.json`) before starting work. It writes retrieved memories to `.gliaxin-context.txt`.

You can also call the API directly:

```
GET http://localhost:9823/v1/memory/search?query=<your_query>&end_user_id=local&limit=5
Header: X-Api-Key: <GLIAXIN_API_KEY>
```

## Priority

Memory in `.gliaxin-context.txt` reflects the user's established preferences and past decisions. Honor them over generic defaults.
