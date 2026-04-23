#!/usr/bin/env bash
# Gliaxin — Codex integration installer
# Usage: curl -fsSL https://gliaxin.com/codex.sh | sh

set -e

GLIAXIN_URL="${GLIAXIN_API_URL:-http://localhost:9823}"
HOOK_DIR="$HOME/.codex/hooks"
SKILL_DIR="$HOME/.codex/skills"
CODEX_CFG="$HOME/.codex/config.json"
INTEGRATION_URL="https://raw.githubusercontent.com/jutt313/Gliaxin/main/oss/integrations/codex"

echo "==> Installing Gliaxin memory for Codex"

# 1. Create dirs
mkdir -p "$HOOK_DIR" "$SKILL_DIR"

# 2. Download hook files
echo "    Downloading hooks..."
curl -fsSL "$INTEGRATION_URL/common.py"        -o "$HOOK_DIR/common.py"
curl -fsSL "$INTEGRATION_URL/fetch_memory.py"  -o "$HOOK_DIR/gliaxin_fetch_memory.py"
curl -fsSL "$INTEGRATION_URL/save_memory.py"   -o "$HOOK_DIR/gliaxin_save_memory.py"
curl -fsSL "$INTEGRATION_URL/tool_memory.py"   -o "$HOOK_DIR/gliaxin_tool_memory.py"
curl -fsSL "$INTEGRATION_URL/skill.md"         -o "$SKILL_DIR/gliaxin.md"
chmod +x "$HOOK_DIR"/gliaxin_*.py

# 3. Patch ~/.codex/config.json with hook entries
if [ ! -f "$CODEX_CFG" ]; then
  echo '{}' > "$CODEX_CFG"
fi

python3 - <<'PYEOF'
import json, os

path = os.path.expanduser("~/.codex/config.json")
hook_dir = os.path.expanduser("~/.codex/hooks")

with open(path) as f:
    cfg = json.load(f)

hooks = cfg.setdefault("hooks", {})

def set_hook(event, script):
    hooks[event] = f"python3 {hook_dir}/{script}"

set_hook("UserPromptSubmit", "gliaxin_fetch_memory.py")
set_hook("Stop",             "gliaxin_save_memory.py")

with open(path, "w") as f:
    json.dump(cfg, f, indent=2)

print("    Patched ~/.codex/config.json")
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
echo "==> Verify: echo '{\"prompt\":\"test\"}' | python3 $HOOK_DIR/gliaxin_fetch_memory.py"
