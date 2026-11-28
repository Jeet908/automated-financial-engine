"""
src/portal/progress_bus.py — Real-Time Job Progress Event Bus.
Provides:
1. Redis Pub/Sub + Redis List history when REDIS_URL is configured (Celery worker execution).
2. Thread-safe in-memory ring buffer & asyncio.Queue listeners for in-process/eager execution, dev, and CI.
3. SSE frame formatting with 15-second keepalive heartbeats and late-connecting client history replay.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any, AsyncGenerator

logger = logging.getLogger(__name__)

# In-memory storage for local/eager execution and test environments
_in_memory_history: dict[str, list[dict[str, Any]]] = {}
_listeners: dict[str, list[asyncio.Queue]] = {}
_lock = threading.Lock()

_redis_client = None
_redis_checked = False


def _get_redis():
    global _redis_client, _redis_checked
    if not _redis_checked:
        _redis_checked = True
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                import redis
                client = redis.Redis.from_url(redis_url, decode_responses=True)
                client.ping()
                _redis_client = client
                logger.info("ProgressBus connected to Redis Pub/Sub at %s", redis_url.split("@")[-1])
            except Exception as exc:
                logger.warning("ProgressBus could not connect to Redis (%s); using in-memory bus.", exc)
                _redis_client = None
    return _redis_client


def emit_job_progress(
    job_id: str,
    stage: str,
    progress_pct: int,
    message: str,
    elapsed_s: float | None = None,
    data: dict[str, Any] | None = None,
    event_type: str = "progress",
) -> dict[str, Any]:
    """
    Publishes a progress milestone event to the event bus.
    Stores the event in history (Redis or in-memory) and distributes it to all active SSE subscribers.
    """
    payload: dict[str, Any] = {
        "job_id": job_id,
        "stage": stage,
        "progress_pct": int(progress_pct),
        "message": message,
        "elapsed_s": round(float(elapsed_s), 2) if elapsed_s is not None else 0.0,
        "event_type": event_type,
        "timestamp": time.time(),
    }
    if data is not None:
        payload["data"] = data

    # 1. Update in-memory history and active local listener queues
    with _lock:
        if job_id not in _in_memory_history:
            _in_memory_history[job_id] = []
        _in_memory_history[job_id].append(payload)
        # Cap in-memory history at 50 events per job
        if len(_in_memory_history[job_id]) > 50:
            _in_memory_history[job_id] = _in_memory_history[job_id][-50:]

        active_queues = list(_listeners.get(job_id, []))

    for q in active_queues:
        try:
            q.put_nowait(payload)
        except Exception:
            pass

    # 2. Redis Pub/Sub and List history (for multi-process Celery workers)
    r = _get_redis()
    if r is not None:
        try:
            json_str = json.dumps(payload)
            r.publish(f"job:progress:{job_id}", json_str)
            r.rpush(f"job:progress:history:{job_id}", json_str)
            r.expire(f"job:progress:history:{job_id}", 300)
        except Exception as exc:
            logger.debug("Redis emit error for job %s: %s", job_id, exc)

    return payload


def get_job_progress_history(job_id: str) -> list[dict[str, Any]]:
    """Retrieves all past progress events for late-connecting SSE clients."""
    r = _get_redis()
    if r is not None:
        try:
            items = r.lrange(f"job:progress:history:{job_id}", 0, -1)
            if items:
                return [json.loads(it) for it in items]
        except Exception as exc:
            logger.debug("Redis history read error for %s: %s", job_id, exc)

    with _lock:
        return list(_in_memory_history.get(job_id, []))


async def subscribe_job_progress(
    job_id: str,
    request: Any = None,
    timeout_s: float = 120.0,
) -> AsyncGenerator[str, None]:
    """
    Subscribes to real-time job progress events, yielding standard Server-Sent Events (SSE) frames:
    event: <event_type>
    data: <json_string>

    Features:
    - Automatically replays past milestones to late-connecting clients.
    - Yields ': keepalive\\n\\n' heartbeats every 15 seconds.
    - Closes cleanly when 'completed' or 'error' event is received.
    """
    # 1. Replay historical milestone frames
    history = get_job_progress_history(job_id)
    seen_stages: set[str] = set()

    for item in history:
        evt = item.get("event_type", "progress")
        stage = item.get("stage")
        if stage:
            seen_stages.add(stage)
        yield f"event: {evt}\ndata: {json.dumps(item)}\n\n"
        if evt in ("completed", "error"):
            return

    # 2. Register local asyncio queue
    q: asyncio.Queue = asyncio.Queue()
    with _lock:
        if job_id not in _listeners:
            _listeners[job_id] = []
        _listeners[job_id].append(q)

    # 3. If Redis is active, start a background task bridging Redis Pub/Sub to the local queue
    redis_task = None
    r = _get_redis()
    if r is not None:
        async def _redis_bridge():
            try:
                pubsub = r.pubsub()
                pubsub.subscribe(f"job:progress:{job_id}")
                loop = asyncio.get_running_loop()
                while True:
                    # Non-blocking get_message running in thread pool
                    msg = await loop.run_in_executor(None, pubsub.get_message, True, 1.0)
                    if msg and msg["type"] == "message":
                        try:
                            data = json.loads(msg["data"])
                            await q.put(data)
                        except Exception:
                            pass
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug("Redis bridge ended for %s: %s", job_id, e)

        redis_task = asyncio.create_task(_redis_bridge())

    start_time = time.time()
    try:
        while True:
            # Check client disconnection
            if request is not None and hasattr(request, "is_disconnected"):
                if await request.is_disconnected():
                    logger.debug("SSE client disconnected from job %s stream.", job_id)
                    break

            # Timeout check
            if time.time() - start_time > timeout_s:
                logger.warning("SSE subscription for job %s timed out after %ss.", job_id, timeout_s)
                break

            try:
                # 15-second heartbeat wait
                item = await asyncio.wait_for(q.get(), timeout=15.0)
                evt = item.get("event_type", "progress")
                yield f"event: {evt}\ndata: {json.dumps(item)}\n\n"
                if evt in ("completed", "error"):
                    break
            except asyncio.TimeoutError:
                # Proxy-safe 15-second keep-alive heartbeat
                yield ": keepalive\n\n"

    finally:
        if redis_task is not None:
            redis_task.cancel()
        with _lock:
            if job_id in _listeners and q in _listeners[job_id]:
                _listeners[job_id].remove(q)
                if not _listeners[job_id]:
                    _listeners.pop(job_id, None)
