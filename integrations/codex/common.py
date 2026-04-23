#!/usr/bin/env python3
"""
Shared helpers for Codex Gliaxin hooks.
Loads env from the project root .env and builds a Gliaxin SDK client.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # points to oss/
SDK_PYTHON_DIR = ROOT / "sdk" / "python"
AGENT_NAME = "codex"

if str(SDK_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(SDK_PYTHON_DIR))


def load_dotenv() -> None:
    env_path = ROOT / ".env"
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


def build_client():
    from gliaxin import Gliaxin
    api_key = os.getenv("GLIAXIN_API_KEY", "").strip()
    if not api_key:
        return None
    base_url = os.getenv("GLIAXIN_API_URL", "http://localhost:9823").strip()
    return Gliaxin(api_key, base_url=base_url, timeout=5.0)


def end_user_id() -> str:
    return (
        os.getenv("GLIAXIN_USER_ID", "").strip()
        or os.getenv("USER", "").strip()
        or "codex-user"
    )


async def ensure_agent_id(client) -> str:
    result = await client.agent.register(AGENT_NAME)
    return result.agent_id
