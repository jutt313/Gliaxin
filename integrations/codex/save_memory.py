#!/usr/bin/env python3
"""
Codex Stop hook.

Saves the last user/assistant turn to Gliaxin using the turn-based memory API.
"""

from __future__ import annotations

import asyncio
import json
import sys

from common import build_client, end_user_id, ensure_agent_id


def text_from_content(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""

    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type in ("input_text", "output_text", "text"):
            text = (block.get("text") or "").strip()
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def last_turn(transcript_path: str) -> tuple[str, str]:
    try:
        with open(transcript_path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except Exception:
        return "", ""

    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except Exception:
            continue

    user_message = ""
    assistant_message = ""

    for event in reversed(events):
        if event.get("type") != "message":
            continue

        role = event.get("role")
        text = text_from_content(event.get("content"))
        if not text:
            continue

        if not assistant_message and role == "assistant":
            assistant_message = text
            continue

        if assistant_message and role == "user":
            user_message = text
            break

    return user_message, assistant_message


async def save_turn(user_message: str, assistant_message: str) -> None:
    if not user_message:
        return

    client = build_client()
    if client is None:
        return

    try:
        agent_id = await ensure_agent_id(client)
        messages = [{"role": "user", "content": user_message}]
        if assistant_message:
            messages.append({"role": "assistant", "content": assistant_message})

        await client.memory.add_turn(
            end_user_id(),
            agent_id,
            messages=messages,
            scope="agent",
        )
    except Exception:
        return


async def run() -> int:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0

    transcript_path = hook_input.get("transcript_path") or ""
    last_assistant = (hook_input.get("last_assistant_message") or "").strip()

    user_message = ""
    assistant_message = last_assistant

    if transcript_path:
        transcript_user, transcript_assistant = last_turn(transcript_path)
        user_message = transcript_user
        if transcript_assistant:
            assistant_message = transcript_assistant

    if len(user_message) < 5:
        return 0

    await save_turn(user_message, assistant_message)
    return 0


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
