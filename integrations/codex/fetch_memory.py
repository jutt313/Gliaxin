#!/usr/bin/env python3
"""
Codex UserPromptSubmit hook.

Fetches relevant Gliaxin memories for the current prompt and injects them as
additional developer context before Codex responds.
"""

from __future__ import annotations

import asyncio
import json
import sys

from common import build_client, end_user_id, ensure_agent_id


async def run() -> int:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0

    prompt = (hook_input.get("prompt") or "").strip()
    if len(prompt) < 10:
        return 0

    client = build_client()
    if client is None:
        return 0

    try:
        agent_id = await ensure_agent_id(client)
        memories = await client.memory.search(
            end_user_id(),
            prompt,
            limit=8,
            agent_id=agent_id,
        )
    except Exception:
        return 0

    lines: list[str] = []
    seen_contents: set[str] = set()
    if memories:
        lines.append("[Gliaxin Memory: relevant context from past conversations]")
        for memory in memories:
            content = memory.content.strip()
            if content:
                category = (memory.category or "other").strip()
                seen_contents.add(content)
                lines.append(f"- [{category}] {content}")

    try:
        raw_records = await client.memory.raw(
            end_user_id(),
            page=1,
            page_size=6,
            agent_id=agent_id,
        )
    except Exception:
        raw_records = None

    raw_count = 0
    if raw_records and raw_records.records:
        if lines:
            lines.append("")
        lines.append("[Gliaxin Memory: recent raw turn context]")
        for record in raw_records.records:
            content = record.content.strip()
            if not content or content in seen_contents:
                continue
            seen_contents.add(content)
            lines.append(f"- {content}")
            raw_count += 1
            if raw_count >= 4:
                break
        if raw_count == 0:
            lines.pop()
            if lines and not lines[-1]:
                lines.pop()

    if not lines:
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(lines),
        }
    }
    sys.stdout.write(json.dumps(output))
    return 0


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
