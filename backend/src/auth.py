"""
OSS auth: simple static API key check against OSS_API_KEY env var.
No Firebase. No database lookup. One key for personal local use.
"""

import os
from fastapi import Header, HTTPException
from dotenv import load_dotenv

load_dotenv()


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> dict:
    expected = os.getenv("OSS_API_KEY", "").strip()
    if not expected:
        raise RuntimeError("OSS_API_KEY is not set in .env")

    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Api-Key header")

    project_id = os.getenv("OSS_PROJECT_ID", "").strip()
    if not project_id:
        raise RuntimeError("OSS_PROJECT_ID is not set in .env")

    return {
        "project_id": project_id,
        "permission": "write",
    }


def require_write(auth: dict) -> None:
    pass  # all OSS keys have write permission


def require_admin(auth: dict) -> None:
    pass  # all OSS keys have admin permission
