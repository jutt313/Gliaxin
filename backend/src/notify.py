"""No-op notification stubs for OSS mode."""


async def push(conn, user_id: str, event_type: str, message: str) -> None:
    pass


async def user_id_for_project(conn, project_id: str) -> str | None:
    return None
