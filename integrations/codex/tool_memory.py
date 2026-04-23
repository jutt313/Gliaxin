#!/usr/bin/env python3
"""
Codex PreToolUse hook for Bash.

Best-effort guardrail that blocks Bash commands targeting ad-hoc memory files.
Codex hooks do not currently intercept Write/Edit tools directly, only Bash.
"""

import json
import os
import shlex
import sys
from pathlib import Path


def load_dotenv() -> None:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv()

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
    if ".codex" in parts and "memory" in parts:
        return True
    if ".claude" in parts and "memory" in parts:
        return True

    return False


def command_targets_blocked_path(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except Exception:
        tokens = command.split()

    for token in tokens:
        stripped = token.strip("\"'")
        if is_blocked_path(stripped):
            return True
    return False


def main() -> int:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0

    tool_input = hook_input.get("tool_input") or {}
    command = tool_input.get("command") or ""
    if not command or not command_targets_blocked_path(command):
        return 0

    sys.stderr.write(
        "BLOCKED: Do not write manual memory files here. "
        "Gliaxin memory is handled by the configured hooks/API.\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
