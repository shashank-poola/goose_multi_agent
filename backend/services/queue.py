"""
arq — async Redis job queue (Python equivalent of BullMQ).

Enqueue from FastAPI:  pool = await get_arq_pool(); await enqueue_research(session_id, pool)
Run worker:            arq backend.services.queue.WorkerSettings
"""

from __future__ import annotations

import arq
from arq.connections import ArqRedis, RedisSettings

from backend.core.config import settings
from backend.core.logger import logger


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def get_arq_pool() -> ArqRedis:
    return await arq.create_pool(_redis_settings())


async def enqueue_research(session_id: str, pool: ArqRedis) -> str:
    """Enqueue an Ultra research job. Returns arq job ID."""
    job = await pool.enqueue_job("run_research_job", session_id, _queue_name="goose:research")
    logger.info("Enqueued research job %s for session %s", job.job_id, session_id)
    return job.job_id


# ---------------------------------------------------------------------------
# Worker task — wired up to the LangGraph Ultra graph at runtime
# ---------------------------------------------------------------------------

async def run_research_job(ctx: dict, session_id: str) -> None:
    """arq worker entry point for async Ultra sessions."""
    from backend.graphs.ultra import run_ultra  # imported here to avoid circular at module load

    logger.info("[worker] Starting Ultra session %s", session_id)
    try:
        await run_ultra(session_id)
        logger.info("[worker] Completed Ultra session %s", session_id)
    except Exception as exc:
        logger.error("[worker] Ultra session %s failed: %s", session_id, exc)
        raise


# ---------------------------------------------------------------------------
# Worker settings — used by `arq backend.services.queue.WorkerSettings`
# ---------------------------------------------------------------------------

class WorkerSettings:
    functions = [run_research_job]
    redis_settings = _redis_settings()
    queue_name = "goose:research"
    job_timeout = 360          # 6 min hard limit per job
    max_jobs = 4               # concurrent Ultra sessions per worker process
    health_check_interval = 30
    retry_jobs = False         # don't silently retry — surface failures to DB
