# Gliaxin Memory Hook for OpenClaw

This hook integrates Gliaxin persistent memory into OpenClaw.

## Events

### `prompt:before`
- Triggered: before each user prompt is sent to the model
- Action: fetches relevant memories from Gliaxin and prepends them to the prompt

### `response:after`
- Triggered: after the model produces a response
- Action: sends the prompt+response turn to Gliaxin for memory extraction

## Handler

See `handler.ts` for the implementation.

## Registration

Add to your OpenClaw config (`~/.openclaw/config.json`):

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

## Environment

```bash
export GLIAXIN_API_KEY="your-oss-api-key"
export GLIAXIN_API_URL="http://localhost:9823"
export GLIAXIN_USER_ID="your-username"
```
