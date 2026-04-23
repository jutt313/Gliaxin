# Gliaxin — OpenClaw Integration

Gives OpenClaw persistent memory using Gliaxin's local API.

## Setup

### 1. Start Gliaxin

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

### 3. Install the hook

```bash
curl -fsSL https://gliaxin.com/openclaw.sh | sh
```

Or manually:

```bash
mkdir -p ~/.openclaw/hooks/gliaxin
cp handler.ts ~/.openclaw/hooks/gliaxin/
cp package.json ~/.openclaw/hooks/gliaxin/
cd ~/.openclaw/hooks/gliaxin && npm install
```

### 4. Register the hook in OpenClaw config

Add to `~/.openclaw/config.json`:

```json
{
  "hooks": [
    {
      "event": "prompt:before",
      "handler": "~/.openclaw/hooks/gliaxin/handler.ts",
      "fn": "beforePrompt"
    },
    {
      "event": "response:after",
      "handler": "~/.openclaw/hooks/gliaxin/handler.ts",
      "fn": "afterResponse"
    }
  ]
}
```

## How it works

- `beforePrompt`: searches Gliaxin for memories relevant to the current prompt and injects them as context
- `afterResponse`: saves the full turn (prompt + response) to Gliaxin for extraction

## Test

```bash
node -e "
const { beforePrompt } = require('./handler.ts');
beforePrompt({ prompt: 'test query' }).then(r => console.log(r.prompt));
"
```

## Troubleshooting

**Hook runs but no memory is injected**

Test the handler directly:
```bash
cd ~/.openclaw/hooks/gliaxin
GLIAXIN_API_KEY=your-key GLIAXIN_API_URL=http://localhost:9823 GLIAXIN_USER_ID=local \
  node -e "import('./handler.ts').then(m => m.beforePrompt({prompt:'test'}).then(r => console.log(r.prompt)))"
```
If output is just `test` with no memory block — either Gliaxin has no memories yet (add some first) or the API isn't reachable. Check with:
```bash
curl http://localhost:9823/health
```

**`afterResponse` silently fails**

Failures in `afterResponse` are intentionally swallowed (non-fatal) so they don't block the agent. To debug, add a temporary `console.error` inside the catch block in `handler.ts`, then watch the OpenClaw logs.

**Hook not registered**

Check `~/.openclaw/config.json` — both `beforePrompt` and `afterResponse` entries need to be there. Re-run the installer if they're missing:
```bash
curl -fsSL https://gliaxin.com/openclaw.sh | sh
```
Then restart OpenClaw.
