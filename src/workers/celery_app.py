from __future__ import annotations

import os

try:
    from celery import Celery
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    Celery = None
    crontab = None
    CELERY_AVAILABLE = False

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
is_eager = (
    os.environ.get("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("true", "1", "yes")
    or not os.environ.get("REDIS_URL")
)

if CELERY_AVAILABLE:
    celery_app = Celery("marketlens", broker=redis_url, backend=redis_url)

    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_always_eager=is_eager,
        task_eager_propagates=True,
        task_routes={
            "src.workers.tasks.live_scrape_task": {"queue": "valuation_heavy"},
            "src.workers.tasks.generate_pack_task": {"queue": "valuation_heavy"},
            "src.workers.tasks.daily_benchmark_refresh_task": {"queue": "scraper_daily"},
        },
        beat_schedule={
            "daily-00-00-utc-scraper-refresh": {
                "task": "src.workers.tasks.daily_benchmark_refresh_task",
                "schedule": crontab(hour=0, minute=0),
                "options": {"queue": "scraper_daily"},
            },
        },
    )
    celery_app.autodiscover_tasks(["src.workers"])
else:
    celery_app = None


def check_redis_connectivity() -> bool:
    """Live probe checking Redis server connectivity."""
    url = os.environ.get("REDIS_URL")
    if not url:
        return False
    try:
        import redis
        client = redis.from_url(url, socket_connect_timeout=2)
        return bool(client.ping())
    except Exception:
        return False
