"""FastAPI entrypoint: lifespan boots background workers, mounts routers."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import pool, open_pool, close_pool
from .baseline import refresh_all_baselines
from .scoring import score_pending
from .routes import logs, baselines, incidents, tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("api")

BASELINE_REFRESH_SECONDS = 30
SCORING_TICK_SECONDS = 2


async def _baseline_loop() -> None:
    while True:
        try:
            with pool.connection() as conn:
                n = refresh_all_baselines(conn)
            if n:
                log.info("refreshed baselines for %d users", n)
        except Exception:
            log.exception("baseline refresh failed")
        await asyncio.sleep(BASELINE_REFRESH_SECONDS)


async def _scoring_loop() -> None:
    while True:
        try:
            with pool.connection() as conn:
                n = score_pending(conn, batch_size=200)
            if n:
                log.info("scored %d events", n)
        except Exception:
            log.exception("scoring tick failed")
        await asyncio.sleep(SCORING_TICK_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    tasks = [
        asyncio.create_task(_baseline_loop(), name="baseline_loop"),
        asyncio.create_task(_scoring_loop(), name="scoring_loop"),
    ]
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        for t in tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        close_pool()


app = FastAPI(title="cloud-triage-api", lifespan=lifespan)
app.include_router(logs.router)
app.include_router(baselines.router)
app.include_router(incidents.router)
app.include_router(tools.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/stats")
def stats() -> dict:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM logs")
        total_logs = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM logs WHERE flagged")
        flagged = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM logs WHERE flagged AND NOT investigated")
        pending = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM incidents")
        incidents_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM baselines")
        baselines_count = cur.fetchone()[0]
    return {
        "total_logs": total_logs,
        "flagged_logs": flagged,
        "pending_investigation": pending,
        "incidents": incidents_count,
        "baselines": baselines_count,
    }
