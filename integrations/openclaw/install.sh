#!/usr/bin/env bash
# Gliaxin — OpenClaw integration installer
# Usage: curl -fsSL https://gliaxin.com/openclaw.sh | sh

set -e

GLIAXIN_URL="${GLIAXIN_API_URL:-http://localhost:9823}"
HOOK_DIR="$HOME/.openclaw/hooks/gliaxin"
OPENCLAW_CFG="$HOME/.openclaw/config.json"
INTEGRATION_URL="https://raw.githubusercontent.com/jutt313/Gliaxin/main/oss/integrations/openclaw"

echo "==> Installing Gliaxin memory for OpenClaw"

# 1. Download hook files
mkdir -p "$HOOK_DIR"
echo "    Downloading handler and skill..."
curl -fsSL "$INTEGRATION_URL/handler.ts"    -o "$HOOK_DIR/handler.ts"
curl -fsSL "$INTEGRATION_URL/package.json"  -o "$HOOK_DIR/package.json"
curl -fsSL "$INTEGRATION_URL/skill.md"      -o "$HOOK_DIR/skill.md"
curl -fsSL "$INTEGRATION_URL/HOOK.md"       -o "$HOOK_DIR/HOOK.md"

# 2. Install npm dependencies
echo "    Installing npm dependencies..."
cd "$HOOK_DIR" && npm install --silent

# 3. Patch ~/.openclaw/config.json
if [ ! -f "$OPENCLAW_CFG" ]; then
  echo '{}' > "$OPENCLAW_CFG"
fi

python3 - <<PYEOF
import json, os

path = os.path.expanduser("~/.openclaw/config.json")
hook_dir = os.path.expanduser("~/.openclaw/hooks/gliaxin")

with open(path) as f:
    cfg = json.load(f)

hooks = cfg.setdefault("hooks", [])

new_hooks = [
    {
        "event": "prompt:before",
        "handler": f"{hook_dir}/handler.ts",
        "fn": "beforePrompt"
    },
    {
        "event": "response:after",
        "handler": f"{hook_dir}/handler.ts",
        "fn": "afterResponse"
    }
]

existing_fns = {h.get("fn") for h in hooks}
for h in new_hooks:
    if h["fn"] not in existing_fns:
        hooks.append(h)

with open(path, "w") as f:
    json.dump(cfg, f, indent=2)

print("    Patched ~/.openclaw/config.json")
PYEOF

# 4. Print env var reminder
echo ""
echo "==> Done. Add these to your shell profile (~/.zshrc or ~/.bashrc):"
echo ""
echo "    export GLIAXIN_API_KEY=\"your-oss-api-key\""
echo "    export GLIAXIN_API_URL=\"$GLIAXIN_URL\""
echo "    export GLIAXIN_USER_ID=\"\$(whoami)\""
echo ""
echo "    Then run: source ~/.zshrc"
echo ""
echo "==> Gliaxin hooks registered in ~/.openclaw/config.json"
