#!/usr/bin/env python3
"""
UserPromptSubmit hook — fetches relevant Gliaxin memories and injects them
as context before Claude responds.

Install: add this file's path to your Claude Code hooks config.
See integrations/claude-code/README.md for setup instructions.
"""
import json
import os
import sys
import urllib.request
import urllib.parse

API_KEY    = os.getenv("GLIAXIN_API_KEY", "")
BASE_URL   = os.getenv("GLIAXIN_API_URL", "http://localhost:9823")
USER_ID    = os.getenv("GLIAXIN_USER_ID", "local")
AGENT_NAME = "claude-code"


def ensure_agent() -> str:
    payload = json.dumps({"name": AGENT_NAME}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/v1/agent/register",
        data=payload,
        headers={"X-Api-Key": API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as r:
            return json.loads(r.read()).get("agent_id", "")
    except Exception:
        return ""


def search(query: str, agent_id: str) -> list[dict]:
    if not API_KEY:
        return []
    params = urllib.parse.urlencode({
        "query": query,
        "end_user_id": USER_ID,
        "limit": "8",
        "agent_id": agent_id,
    })
    req = urllib.request.Request(f"{BASE_URL}/v1/memory/search?{params}", headers={"X-Api-Key": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read()).get("memories", [])
    except Exception:
        return []


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({}))
        return

    prompt = hook_input.get("prompt") or hook_input.get("message", "")
    if not prompt or len(prompt) < 10:
        print(json.dumps({}))
        return

    agent_id = ensure_agent()
    memories = search(prompt, agent_id)
    if not memories:
        print(json.dumps({}))
        return

    lines = ["[Gliaxin Memory — relevant context from past conversations:]"]
    for m in memories:
        lines.append(f"• {m['content']}")

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(lines),
        }
    }))


if __name__ == "__main__":
    main()
