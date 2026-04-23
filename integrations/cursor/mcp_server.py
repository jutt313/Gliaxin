#!/usr/bin/env python3
"""
Gliaxin MCP Server for Cursor.
Exposes memory_search and memory_add as MCP tools.

Run: python3 mcp_server.py
Add to Cursor MCP config: { "command": "python3", "args": ["/path/to/mcp_server.py"] }
"""

import asyncio
import json
import os
import sys
import urllib.request
import urllib.error
from typing import Any

API_URL = os.getenv("GLIAXIN_API_URL", "http://localhost:9823")
API_KEY = os.getenv("GLIAXIN_API_KEY", "")
USER_ID = os.getenv("GLIAXIN_USER_ID", "local")


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"X-Api-Key": API_KEY, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}


def handle_call(tool: str, params: dict) -> dict:
    if tool == "memory_search":
        query = params.get("query", "")
        limit = params.get("limit", 5)
        result = _request(
            "GET",
            f"/v1/memory/search?query={urllib.parse.quote(query)}&end_user_id={USER_ID}&limit={limit}",
        )
        memories = result.get("memories", [])
        if not memories:
            return {"content": "No relevant memories found."}
        lines = [m.get("content", "") for m in memories]
        return {"content": "\n".join(lines)}

    if tool == "memory_add":
        messages = params.get("messages", [])
        result = _request(
            "POST",
            "/v1/memory/add",
            {"end_user_id": USER_ID, "messages": messages},
        )
        return {"content": f"Saved. layer_a_id={result.get('layer_a_id', '?')}"}

    return {"error": f"Unknown tool: {tool}"}


TOOLS = [
    {
        "name": "memory_search",
        "description": "Search Gliaxin memory for relevant past context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_add",
        "description": "Save a conversation turn to Gliaxin memory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                }
            },
            "required": ["messages"],
        },
    },
]


def mcp_loop():
    import urllib.parse

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg_id = msg.get("id")
        method = msg.get("method", "")

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "gliaxin-mcp", "version": "1.0.0"},
                },
            }
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
        elif method == "tools/call":
            params = msg.get("params", {})
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            result = handle_call(tool_name, tool_args)
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": result.get("content", result.get("error", ""))}]
                },
            }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    import urllib.parse
    mcp_loop()
