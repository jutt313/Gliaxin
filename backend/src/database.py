import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

_pool = None

ENUM_TYPES = [
    'ProjectType', 'ProcessingStatus', 'Category',
    'MemoryType', 'Scope', 'MemoryStatus', 'ConflictStatus', 'AuditAction',
]


async def _init_conn(conn):
    for enum_type in ENUM_TYPES:
        await conn.set_type_codec(
            enum_type, encoder=str, decoder=str, schema='public', format='text'
        )


async def get_pool() -> asyncpg.Pool:
    global _pool
    current_loop = asyncio.get_running_loop()
    if _pool is not None:
        if getattr(_pool, "_closed", False):
            _pool = None
        elif getattr(_pool, "_loop", None) is not current_loop:
            try:
                _pool.terminate()
            except Exception:
                pass
            _pool = None
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL"), init=_init_conn)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        try:
            await _pool.close()
        except RuntimeError:
            _pool.terminate()
        _pool = None
