import asyncio
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from database import get_pool, close_pool
from worker import process_pending
from logger import get_logger
from metrics import record_http_request, render_metrics
from bootstrap import ensure_personal_project
from routes.agents import public_router as agents_public_router
from routes.memory import router as memory_router

load_dotenv()
log = get_logger("gliaxin.main")
WORKER_POLL_INTERVAL = 30


async def _worker_poll_loop() -> None:
    log.info("worker poll loop started", interval=WORKER_POLL_INTERVAL)
    while True:
        await asyncio.sleep(WORKER_POLL_INTERVAL)
        try:
            await process_pending()
        except Exception as exc:
            log.error("worker poll error", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    log.info("db pool connected")
    await ensure_personal_project()
    poll_task = None
    if not os.getenv("TESTING"):
        poll_task = asyncio.create_task(_worker_poll_loop())
    yield
    if poll_task:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass
    await close_pool()
    log.info("db pool closed")


app = FastAPI(title="Gliaxin OSS API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def _request_logger(request: Request, call_next):
    start = time.perf_counter()
    path = request.scope.get("route").path if request.scope.get("route") else request.url.path
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    except Exception:
        status = 500
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        record_http_request(request.method, path, status, duration_ms)
        log.exception("request failed", method=request.method, path=path, status=status)
        raise
    finally:
        if "status" in locals() and status != 500:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            record_http_request(request.method, path, status, duration_ms)
            log.info("request", method=request.method, path=path, status=status, duration_ms=duration_ms)


cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_public_router)
app.include_router(memory_router)


@app.get("/health")
async def health():
    pool = await get_pool()
    async with pool.acquire() as conn:
        pending = await conn.fetchval(
            '''SELECT COUNT(*)::int FROM "LayerA"
               WHERE processing_status IN ('pending', 'processing')'''
        )
    return {
        "ok": True,
        "service": "gliaxin-oss",
        "pending_raw_count": pending,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/metrics")
async def metrics():
    pool = await get_pool()
    async with pool.acquire() as conn:
        queue_depth = await conn.fetchval(
            '''SELECT COUNT(*)::int FROM "LayerA" WHERE processing_status = 'pending' '''
        )
        processing_depth = await conn.fetchval(
            '''SELECT COUNT(*)::int FROM "LayerA" WHERE processing_status = 'processing' '''
        )
        failed_depth = await conn.fetchval(
            '''SELECT COUNT(*)::int FROM "LayerA" WHERE processing_status = 'failed' '''
        )
        pending_conflicts = await conn.fetchval(
            '''SELECT COUNT(*)::int FROM "Conflict" WHERE status = 'pending' '''
        )
    body = render_metrics({
        "gliaxin_worker_queue_pending": queue_depth or 0,
        "gliaxin_worker_queue_processing": processing_depth or 0,
        "gliaxin_worker_queue_failed": failed_depth or 0,
        "gliaxin_conflicts_pending": pending_conflicts or 0,
    })
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4")
