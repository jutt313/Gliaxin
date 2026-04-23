"""
Shared async HTTP client used by all namespaces.
"""
import httpx
from .exceptions import (
    AuthError, NotFoundError, ValidationError, RateLimitError, ServerError, GliaxinError,
)

_STATUS_MAP = {
    400: ValidationError,
    401: AuthError,
    404: NotFoundError,
    429: RateLimitError,
}


def _raise(status: int, body: dict) -> None:
    detail = body.get("detail", "Unknown error")
    exc_cls = _STATUS_MAP.get(status)
    if exc_cls:
        raise exc_cls(detail, status_code=status)
    if status >= 500:
        raise ServerError(detail, status_code=status)
    raise GliaxinError(detail, status_code=status)


class HttpClient:
    def __init__(self, api_key: str, base_url: str, timeout: float):
        self._headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        }
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    async def get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as c:
            r = await c.get(f"{self._base}{path}", headers=self._headers, params=params)
        if not r.is_success:
            _raise(r.status_code, r.json() if r.content else {})
        return r.json()

    async def post(self, path: str, json: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as c:
            r = await c.post(f"{self._base}{path}", headers=self._headers, json=json or {})
        if not r.is_success:
            _raise(r.status_code, r.json() if r.content else {})
        return r.json()

    async def delete(self, path: str, json: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as c:
            r = await c.request(
                "DELETE", f"{self._base}{path}",
                headers=self._headers, json=json or {},
            )
        if not r.is_success:
            _raise(r.status_code, r.json() if r.content else {})
        return r.json()
