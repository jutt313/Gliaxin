#!/usr/bin/env python3
"""
PreToolUse hook — blocks writes to ad-hoc memory files.

Gliaxin memory in this workspace is handled by hooks + API calls, so Claude
should not try to persist memory by writing local MEMORY.md-style files.
"""
import json
import os
import sys


BLOCKED_BASENAMES = {
    "memory.md",
    "memories.md",
    "conversation_memory.md",
}

def is_blocked_path(file_path: str) -> bool:
    if not file_path:
        return False

    normalized = os.path.normpath(file_path)
    lowered = normalized.lower()
    basename = os.path.basename(lowered)

    if basename in BLOCKED_BASENAMES:
        return True

    parts = {part.lower() for part in normalized.split(os.sep) if part}
    if ".claude" in parts and "memory" in parts:
        return True

    return False


def main() -> int:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0

    tool_input = hook_input.get("tool_input", {})
    file_path = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("target_file")
        or ""
    )

    if not is_blocked_path(file_path):
        return 0

    sys.stderr.write(
        "BLOCKED: Do not write manual memory files here. "
        "Gliaxin memory is handled automatically by the configured hooks/API.\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
