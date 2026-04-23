#!/usr/bin/env bash
# Gliaxin — Claude Code integration installer
# Usage: curl -fsSL https://gliaxin.com/claude-code.sh | sh

set -e

GLIAXIN_URL="${GLIAXIN_API_URL:-http://localhost:9823}"
HOOK_DIR="$HOME/.claude/hooks"
SKILL_DIR="$HOME/.claude/skills"
INTEGRATION_URL="https://raw.githubusercontent.com/jutt313/Gliaxin/main/oss/integrations/claude-code"

echo "==> Installing Gliaxin memory for Claude Code"

# 1. Create hook + skill dirs
mkdir -p "$HOOK_DIR" "$SKILL_DIR"

# 2. Download hook files
echo "    Downloading hooks..."
curl -fsSL "$INTEGRATION_URL/fetch_memory.py"  -o "$HOOK_DIR/gliaxin_fetch_memory.py"
curl -fsSL "$INTEGRATION_URL/save_memory.py"   -o "$HOOK_DIR/gliaxin_save_memory.py"
curl -fsSL "$INTEGRATION_URL/tool_memory.py"   -o "$HOOK_DIR/gliaxin_tool_memory.py"
curl -fsSL "$INTEGRATION_URL/skill.md"         -o "$SKILL_DIR/gliaxin.md"
chmod +x "$HOOK_DIR"/gliaxin_*.py

# 3. Patch ~/.claude/settings.json with hook entries
SETTINGS="$HOME/.claude/settings.json"
if [ ! -f "$SETTINGS" ]; then
  echo '{}' > "$SETTINGS"
fi

python3 - <<'PYEOF'
import json, os, sys

path = os.path.expanduser("~/.claude/settings.json")
hook_dir = os.path.expanduser("~/.claude/hooks")

with open(path) as f:
    cfg = json.load(f)

hooks = cfg.setdefault("hooks", {})

def add_hook(event, script):
    entry = {"type": "command", "command": f"python3 {hook_dir}/{script}"}
    existing = hooks.setdefault(event, [])
    cmds = [h.get("command","") for h in existing if isinstance(h,dict)]
    if entry["command"] not in cmds:
        existing.append(entry)

add_hook("UserPromptSubmit", "gliaxin_fetch_memory.py")
add_hook("Stop",             "gliaxin_save_memory.py")
add_hook("PreToolUse",       "gliaxin_tool_memory.py")

with open(path, "w") as f:
    json.dump(cfg, f, indent=2)

print("    Patched ~/.claude/settings.json")
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
echo "==> Verify: echo '\{\"prompt\":\"test\"}' | python3 $HOOK_DIR/gliaxin_fetch_memory.py"
