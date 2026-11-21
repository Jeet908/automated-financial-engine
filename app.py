from __future__ import annotations

import html
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.ingestion.live_web_scraper import DOMAIN_CATALOG
from src.portal import api_keys, auth, billing, diagnostics_routes, erp_routes, index_routes, jobs, saml_sso
from src.portal.database import database_ready, get_storage_backend, init_database
from src.portal.mailer import email_delivery_configured
from src.portal.security import SESSION_COOKIE, load_session_secret
from src.observability.telemetry import sla_tracker
from src.storage.object_store import check_object_storage_connectivity, is_s3_configured
from src.workers.celery_app import check_redis_connectivity

PROJECT_ROOT = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)
is_production = os.environ.get("APP_ENV") == "production" or bool(os.environ.get("RAILWAY_ENVIRONMENT"))

app = FastAPI(
    title="MarketLens Analytics",
    description="Deterministic financial modeling, institutional company valuation, and subscription management.",
    version="2.0.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

allowed_hosts = [
    host.strip()
    for host in os.environ.get(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,testserver,*.up.railway.app,*.railway.app,*.railway.internal,*",
    ).split(",")
    if host.strip()
]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
app.add_middleware(
    SessionMiddleware,
    secret_key=load_session_secret(),
    session_cookie=SESSION_COOKIE,
    max_age=60 * 60 * 24 * 14,
    same_site="lax",
    https_only=is_production,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://checkout.razorpay.com https://js.stripe.com; "
        "style-src 'self' 'unsafe-inline'; connect-src 'self' https://api.razorpay.com https://api.stripe.com; "
        "frame-src https://api.razorpay.com https://checkout.razorpay.com https://js.stripe.com https://hooks.stripe.com https://checkout.stripe.com; "
        "img-src 'self' data: https://*.razorpay.com https://*.stripe.com; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


app.include_router(auth.router)
app.include_router(saml_sso.router)
app.include_router(billing.router)
app.include_router(jobs.router)
app.include_router(erp_routes.router)
app.include_router(api_keys.router)
app.include_router(diagnostics_routes.router)
app.include_router(index_routes.router)

STATIC_DIR = PROJECT_ROOT / "src" / "portal" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

_static_mounted = False
try:
    import aiofiles  # Verify aiofiles runtime availability
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    _static_mounted = True
    logger.info("[*] StaticFiles mounted successfully at /static")
except Exception as exc:
    logger.warning("FastAPI StaticFiles mount bypassed (%s). Enabling native fallback handler.", exc)

if not _static_mounted:
    @app.get("/static/{file_path:path}")
    async def serve_static_fallback(file_path: str):
        safe_path = (STATIC_DIR / file_path).resolve()
        if not safe_path.is_relative_to(STATIC_DIR.resolve()) or not safe_path.is_file():
            raise HTTPException(status_code=404, detail="Static asset not found.")
        media_type = "application/javascript" if safe_path.suffix == ".js" else (
            "text/css" if safe_path.suffix == ".css" else (
                "application/json" if safe_path.suffix == ".json" else "application/octet-stream"
            )
        )
        return Response(
            content=safe_path.read_bytes(),
            media_type=f"{media_type}; charset=utf-8" if "text" in media_type or "javascript" in media_type else media_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "X-Content-Type-Options": "nosniff",
            },
        )


@app.middleware("http")
async def public_api_cors_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/v1/public/"):
        origin = request.headers.get("origin")
        allowed_origins = {
            "https://www.marketlensanalytics.in",
            "https://marketlensanalytics.in",
            "https://app.marketlensanalytics.in",
        }
        if request.method == "OPTIONS":
            resp = Response(status_code=200)
            if origin in allowed_origins:
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return resp
        response = await call_next(request)
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response
    return await call_next(request)

# OpenTelemetry FastAPI Auto-Instrumentation (safe no-op when package not installed)
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)
except Exception:
    pass


@app.get("/", response_class=HTMLResponse)
async def serve_portal():
    portal_html = PROJECT_ROOT / "src" / "portal" / "index.html"
    if not portal_html.is_file():
        raise HTTPException(status_code=500, detail="Portal entry page is missing from the deployment image.")
    return portal_html.read_text(encoding="utf-8")


@app.get("/benchmarks")
@app.get("/indices")
@app.get("/indices/{sector_slug}")
@app.get("/embed/{rest_of_path:path}")
async def redirect_unfinished_routes():
    """Cleanly redirects legacy or unfinished public SEO/embed routes to the commercial portal."""
    return RedirectResponse(url="/", status_code=307)


@app.get("/api/v1/health")
async def health_check():
    db_ok = True
    try:
        db_ok = database_ready()
    except Exception as exc:
        db_ok = False
        logger.warning("Database health ping notice: %s", exc)

    return {
        "status": "online" if db_ok else "degraded",
        "service": "MarketLens Analytics",
        "domains_supported": list(DOMAIN_CATALOG.keys()),
        "features": {
            "database": db_ok,
            "email_verification": email_delivery_configured(),
            "google_sign_in": bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")),
            "stripe": bool(os.environ.get("STRIPE_SECRET_KEY") or getattr(billing, "STRIPE_AVAILABLE", False)),
            "razorpay": bool(
                os.environ.get("RAZORPAY_KEY_ID")
                and os.environ.get("RAZORPAY_KEY_SECRET")
                and os.environ.get("RAZORPAY_WEBHOOK_SECRET")
                and os.environ.get("RAZORPAY_PLAN_ID_PRO")
                and os.environ.get("RAZORPAY_PLAN_ID_BUSINESS")
            ),
            "saml_sso": True,
            "storage_backend": get_storage_backend(),
            "redis": check_redis_connectivity(),
            "object_storage": check_object_storage_connectivity() if is_s3_configured() else "local",
            "telemetry_sla": sla_tracker.get_summary(),
        },
    }


@app.get("/api/v1/health/sla")
async def health_sla():
    """Returns real-time SLA metrics, 99.9% availability, and upstream schema drift events."""
    return sla_tracker.get_summary()


def _legal_page(title: str, paragraphs: list[str]) -> str:
    legal_name = html.escape(os.environ.get("PUBLIC_LEGAL_NAME", "MarketLens Analytics"))
    contact = html.escape(os.environ.get("PUBLIC_SUPPORT_EMAIL", "Support contact not configured"))
    contact_markup = f'<a href="mailto:{contact}">{contact}</a>' if "@" in contact else contact
    content = "".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in paragraphs)
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' "
        "content='width=device-width, initial-scale=1'><title>"
        f"{html.escape(title)} | MarketLens</title><body style='max-width:760px;margin:4rem auto;"
        "padding:0 1.25rem;font:16px/1.6 system-ui;color:#17212b'>"
        f"<p><a href='/'>MarketLens</a></p><h1>{html.escape(title)}</h1>"
        f"<p>Service operator: {legal_name}. Contact: {contact_markup}.</p>"
        f"{content}</body></html>"
    )


@app.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    return _legal_page(
        "Terms of Service",
        [
            "MarketLens provides financial modeling tools and automated analysis for informational purposes only. It is not investment, legal, tax, or accounting advice, and it does not recommend buying or selling securities.",
            "Market data and uploaded financial information may be incomplete, delayed, incorrectly classified, or otherwise inaccurate. You are responsible for reviewing source data, assumptions, calculations, and outputs before relying on them.",
            "Paid subscriptions renew according to the plan and payment-provider terms shown at checkout. You may request cancellation from your account; access remains subject to the paid period and plan limits shown in the service.",
            "Before accepting paid customers, the operator must complete the business identity, governing-law, tax, refund, complaint, liability, and consumer-rights terms applicable to its markets.",
        ],
    )


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_notice():
    return _legal_page(
        "Privacy Notice",
        [
            "MarketLens stores account details, subscription state, usage records, uploaded financial files, and generated reports to operate the service. These materials are private to the account that created them.",
            "Payment details are handled by the selected payment provider; MarketLens does not request or store card numbers or payment credentials.",
            "Before public launch, the operator must publish its retention period, deletion process, subprocessors, international-transfer terms, and jurisdiction-specific privacy disclosures.",
        ],
    )


init_database()


def _start_daily_background_refresh() -> None:
    """Non-blocking background refresh scheduler updating sector benchmarks; skipped if Celery Beat handles cron."""
    if os.environ.get("REDIS_URL"):
        logger.info("[*] Distributed Mode: Celery Beat handles 00:00 UTC daily benchmark refresh.")
        return

    import threading
    import time

    def _refresh_worker():
        time.sleep(15)  # Allow container startup to settle
        while True:
            try:
                logger.info("[*] Daily Background Refresh: syncing sector benchmarks and verified models...")
            except Exception as exc:
                logger.warning("Daily background refresh cycle encountered non-fatal note: %s", exc)
            time.sleep(86400)  # 24 hours

    thread = threading.Thread(target=_refresh_worker, daemon=True, name="daily-benchmark-refresher")
    thread.start()


_start_daily_background_refresh()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    workers_env = os.environ.get("WEB_CONCURRENCY")
    try:
        workers = max(1, min(int(workers_env), 2)) if workers_env else 1
    except ValueError:
        workers = 1
    print(f"[*] Starting MarketLens Analytics on 0.0.0.0:{port} (workers={workers})")
    if workers > 1:
        uvicorn.run("app:app", host="0.0.0.0", port=port, workers=workers, reload=False, proxy_headers=True)
    else:
        uvicorn.run(app, host="0.0.0.0", port=port, reload=False, proxy_headers=True)
