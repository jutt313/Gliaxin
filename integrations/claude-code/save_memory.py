#!/usr/bin/env python3
"""
Stop hook — saves the full conversation turn (user + assistant) to Gliaxin.

Install: add this file's path to your Claude Code hooks config.
See integrations/claude-code/README.md for setup instructions.
"""
import json
import os
import sys
import urllib.request

API_KEY    = os.getenv("GLIAXIN_API_KEY", "")
BASE_URL   = os.getenv("GLIAXIN_API_URL", "http://localhost:9823")
USER_ID    = os.getenv("GLIAXIN_USER_ID", "local")
AGENT_NAME = "claude-code"

SKIP_PREFIXES = (
    "<local-command", "<command-name>", "<command-message>",
    "<command-args>", "<local-command-stdout>", "# Update Config",
)


def _text_from_content(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [block.get("text", "").strip() for block in content
                 if isinstance(block, dict) and block.get("type") == "text"]
        return " ".join(p for p in parts if p)
    return ""


def last_turn(transcript_path: str) -> tuple[str, str]:
    try:
        with open(transcript_path) as f:
            lines = f.readlines()
    except Exception:
        return "", ""

    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except Exception:
            continue

    user_msg = ""
    assistant_msg = ""

    for event in reversed(events):
        msg = event.get("message", {})
        role = msg.get("role", "")
        text = _text_from_content(msg.get("content", ""))
        if not text:
            continue
        if not assistant_msg and role == "assistant":
            assistant_msg = text
            continue
        if assistant_msg and role in ("human", "user"):
            if any(text.startswith(p) for p in SKIP_PREFIXES):
                break
            user_msg = text
            break

    return user_msg, assistant_msg


def ensure_agent() -> str:
    payload = json.dumps({"name": AGENT_NAME}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/v1/agent/register",
        data=payload,
        headers={"X-Api-Key": API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read()).get("agent_id", "")
    except Exception:
        return ""


def save_turn(user_msg: str, assistant_msg: str, agent_id: str) -> None:
    if not API_KEY:
        return
    messages = [{"role": "user", "content": user_msg}]
    if assistant_msg:
        messages.append({"role": "assistant", "content": assistant_msg})
    payload = json.dumps({
        "end_user_id": USER_ID,
        "agent_id": agent_id,
        "scope": "agent",
        "messages": messages,
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/v1/memory/add",
        data=payload,
        headers={"X-Api-Key": API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            r.read()
    except Exception:
        pass


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        return

    transcript_path = hook_input.get("transcript_path", "")
    if not transcript_path:
        return

    user_msg, assistant_msg = last_turn(transcript_path)
    if not user_msg or len(user_msg) < 5:
        return

    agent_id = ensure_agent()
    save_turn(user_msg, assistant_msg, agent_id)


if __name__ == "__main__":
    main()
