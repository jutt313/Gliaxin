# Gliaxin — GitHub Copilot Integration

Gives GitHub Copilot persistent memory using Gliaxin's local API.

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
curl -fsSL https://gliaxin.com/copilot.sh | sh
```

### 3. Set environment variables

```bash
export GLIAXIN_API_KEY="your-secret-api-key-here"
export GLIAXIN_API_URL="http://localhost:9823"
export GLIAXIN_USER_ID="$(whoami)"
```

### 4. Add Copilot instructions to your project

```bash
mkdir -p .github
cp ~/.gliaxin/copilot/copilot-instructions.md .github/copilot-instructions.md
```

This file tells Copilot to use `.gliaxin-context.txt` as memory context.

### 5. Add VS Code tasks

```bash
mkdir -p .vscode
cp ~/.gliaxin/copilot/vscode-tasks.json .vscode/tasks.json
```

This adds a "Fetch Gliaxin Memory" task that runs on folder open.

## How to use

- Open VS Code → run task "Fetch Gliaxin Memory" (or it runs automatically on folder open)
- Copilot reads `.gliaxin-context.txt` via `copilot-instructions.md`
- Manually fetch any time:

```bash
python3 ~/.gliaxin/copilot/fetch_memory.py "what I'm working on"
```

## Files

| File | Purpose |
|---|---|
| `copilot-instructions.md` | Repo-scoped instruction file for Copilot |
| `vscode-tasks.json` | VS Code task to fetch memory |
| `fetch_memory.py` | CLI helper to fetch + write `.gliaxin-context.txt` |
| `skill.md` | Copilot skill definition |
| `install.sh` | One-command installer |

## Troubleshooting

**`fetch_memory.py` returns nothing**

Run it with a query and check the output:
```bash
GLIAXIN_API_KEY=your-key python3 ~/.gliaxin/copilot/fetch_memory.py "what I'm working on"
```
`connection refused` → start Gliaxin: `docker compose up -d` from the `oss/` folder.
`401 Unauthorized` → `GLIAXIN_API_KEY` doesn't match `OSS_API_KEY` in `.env`.

**`.gliaxin-context.txt` is empty after running the VS Code task**

Open the VS Code Output panel and select "Fetch Gliaxin Memory" to see the task output. If Gliaxin returned memories but the file is empty, check that `jq` is installed (`brew install jq` on Mac). The task uses `jq` to parse the JSON response.

Actually, the task uses Python for parsing — so if the file is empty it means no memories exist yet. Add a few turns first via `POST /v1/memory/add`, wait ~10 seconds for extraction, then fetch again.

**Copilot ignores `copilot-instructions.md`**

The file must be at `.github/copilot-instructions.md` inside the opened project folder. Reload the VS Code window after adding it (`Cmd+Shift+P` → "Reload Window").

## Coming soon

A native Copilot Extension that calls Gliaxin search/add without needing the context file workaround.
