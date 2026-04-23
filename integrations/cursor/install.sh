#!/usr/bin/env bash
# Gliaxin — Cursor integration installer
# Usage: curl -fsSL https://gliaxin.com/cursor.sh | sh

set -e

GLIAXIN_URL="${GLIAXIN_API_URL:-http://localhost:9823}"
INSTALL_DIR="$HOME/.gliaxin/cursor"
INTEGRATION_URL="https://raw.githubusercontent.com/jutt313/Gliaxin/main/oss/integrations/cursor"

echo "==> Installing Gliaxin memory for Cursor"

# 1. Download files
mkdir -p "$INSTALL_DIR"
echo "    Downloading MCP server and skill..."
curl -fsSL "$INTEGRATION_URL/mcp_server.py"  -o "$INSTALL_DIR/mcp_server.py"
curl -fsSL "$INTEGRATION_URL/skill.md"       -o "$INSTALL_DIR/skill.md"
curl -fsSL "$INTEGRATION_URL/.cursorrules"   -o "$INSTALL_DIR/.cursorrules"
chmod +x "$INSTALL_DIR/mcp_server.py"

# 2. Write Cursor MCP config snippet
MCP_SNIPPET="$INSTALL_DIR/cursor_mcp_config.json"
cat > "$MCP_SNIPPET" <<JSON
{
  "mcpServers": {
    "gliaxin": {
      "command": "python3",
      "args": ["$INSTALL_DIR/mcp_server.py"],
      "env": {
        "GLIAXIN_API_KEY": "\${GLIAXIN_API_KEY}",
        "GLIAXIN_API_URL": "$GLIAXIN_URL",
        "GLIAXIN_USER_ID": "\${GLIAXIN_USER_ID}"
      }
    }
  }
}
JSON

echo ""
echo "==> Add this to your Cursor MCP config (~/.cursor/mcp.json):"
echo ""
cat "$MCP_SNIPPET"
echo ""
echo "==> Or for .cursorrules (simpler, no MCP needed):"
echo "    Copy $INSTALL_DIR/.cursorrules to your project root."
echo ""
echo "==> Add these to your shell profile (~/.zshrc or ~/.bashrc):"
echo ""
echo "    export GLIAXIN_API_KEY=\"your-oss-api-key\""
echo "    export GLIAXIN_API_URL=\"$GLIAXIN_URL\""
echo "    export GLIAXIN_USER_ID=\"\$(whoami)\""
echo ""
echo "==> Done."
