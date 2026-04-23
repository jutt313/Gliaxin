#!/usr/bin/env bash
# Gliaxin — GitHub Copilot integration installer
# Usage: curl -fsSL https://gliaxin.com/copilot.sh | sh

set -e

GLIAXIN_URL="${GLIAXIN_API_URL:-http://localhost:9823}"
INSTALL_DIR="$HOME/.gliaxin/copilot"
INTEGRATION_URL="https://raw.githubusercontent.com/jutt313/Gliaxin/main/oss/integrations/copilot"

echo "==> Installing Gliaxin memory for GitHub Copilot"

# 1. Download helper files
mkdir -p "$INSTALL_DIR"
echo "    Downloading fetch helper and skill..."
curl -fsSL "$INTEGRATION_URL/fetch_memory.py"          -o "$INSTALL_DIR/fetch_memory.py"
curl -fsSL "$INTEGRATION_URL/skill.md"                 -o "$INSTALL_DIR/skill.md"
curl -fsSL "$INTEGRATION_URL/copilot-instructions.md"  -o "$INSTALL_DIR/copilot-instructions.md"
curl -fsSL "$INTEGRATION_URL/vscode-tasks.json"        -o "$INSTALL_DIR/vscode-tasks.json"
chmod +x "$INSTALL_DIR/fetch_memory.py"

# 2. Print setup instructions
echo ""
echo "==> Setup steps:"
echo ""
echo "  1. Copy copilot-instructions.md into your project:"
echo "     mkdir -p .github && cp $INSTALL_DIR/copilot-instructions.md .github/copilot-instructions.md"
echo ""
echo "  2. Add VS Code tasks to your project:"
echo "     mkdir -p .vscode && cp $INSTALL_DIR/vscode-tasks.json .vscode/tasks.json"
echo ""
echo "  3. Add these to your shell profile (~/.zshrc or ~/.bashrc):"
echo ""
echo "     export GLIAXIN_API_KEY=\"your-oss-api-key\""
echo "     export GLIAXIN_API_URL=\"$GLIAXIN_URL\""
echo "     export GLIAXIN_USER_ID=\"\$(whoami)\""
echo ""
echo "  4. Fetch memory before a session:"
echo "     python3 $INSTALL_DIR/fetch_memory.py \"current task\""
echo "     # Writes .gliaxin-context.txt — Copilot picks it up via copilot-instructions.md"
echo ""
echo "==> Done."
