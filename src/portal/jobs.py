from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.cli import SUPPORTED_EXTS
from src.storage import object_store
from src.workers.celery_app import celery_app
from src.workers.tasks import generate_pack_task, live_scrape_task

from . import database
from .database import (
    DATA_DIR,
    Job,
    User,
    get_db,
    get_tenant_job,
    init_database,
    list_tenant_jobs,
    utc_now,
)
from .dependencies import get_verified_user
from .plans import account_summary, reserve_job
from .security import check_csrf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["valuation"])
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
FILE_DETAILS = {
    "dashboard_html": ("text/html; charset=utf-8", False),
    "investment_memo_md": ("text/markdown; charset=utf-8", True),
    "audit_certificate_json": ("application/json", True),
    "valuation_output_json": ("application/json", True),
    "engine_model_xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True),
    "zip_pack": ("application/zip", True),
    "xlsx_model": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True),
    "pdf_tearsheet": ("application/pdf", True),
    "pptx_pitchbook": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", True),
}


class LiveScrapeRequest(BaseModel):
    domain: str | None = Field(default="Any Random Domain", max_length=120)
    market: str = Field(default="random", pattern="^(india|us|global|random)$")


def _job_workspace(user_id: str, job_id: str) -> Path:
    return DATA_DIR / "accounts" / user_id / "jobs" / job_id


def _update_job(job_id: str, *, status: str, result: dict[str, Any] | None = None, error_code: str | None = None) -> None:
    init_database()
    with database.SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("Background valuation job %s disappeared from storage.", job_id)
            return
        job.status = status
        job.updated_at = utc_now()
        job.error_code = error_code
        job.result_json = json.dumps(result) if result is not None else None
        db.commit()


def _run_live_job_fallback(job_id: str, user_id: str, domain: str | None, market: str) -> None:
    """Fallback in-process execution when Celery is not active."""
    try:
        live_scrape_task(None, job_id, user_id, domain, market)
    except Exception as exc:
        logger.exception("Fallback live valuation job failed for %s: %s", job_id, exc)


def _run_upload_job_fallback(job_id: str, user_id: str, input_path: str) -> None:
    """Fallback in-process execution for file uploads when Celery is not active."""
    try:
        generate_pack_task(None, job_id, user_id, input_path)
    except Exception as exc:
        logger.exception("Fallback upload valuation job failed for %s: %s", job_id, exc)


@router.post("/model/live-scrape", status_code=202)
def live_scrape(
    payload: LiveScrapeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    check_csrf(request)
    job_id = str(uuid4())
    workspace = _job_workspace(user.id, job_id)
    job = reserve_job(db, user, "live_scrape", workspace)
    try:
        workspace.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.exception("Could not allocate private workspace for job %s.", job.id)
        _update_job(job.id, status="failed", error_code="workspace_unavailable")
        raise HTTPException(status_code=503, detail="Private report storage is temporarily unavailable.")

    # Celery dispatch with non-blocking fallback
    use_celery = bool(os.environ.get("REDIS_URL")) and celery_app is not None
    if use_celery:
        try:
            live_scrape_task.apply_async(
                args=[job.id, user.id, payload.domain, payload.market],
                queue="valuation_heavy",
            )
        except Exception as exc:
            logger.warning("Failed to enqueue live_scrape_task via Celery (%s); falling back to background thread.", exc)
            background_tasks.add_task(_run_live_job_fallback, job.id, user.id, payload.domain, payload.market)
    else:
        background_tasks.add_task(_run_live_job_fallback, job.id, user.id, payload.domain, payload.market)

    return {"job_id": job.id, "status": job.status}


@router.post("/model/generate-pack", status_code=202)
async def generate_pack(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    check_csrf(request)
    filename = Path(file.filename or "upload").name
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTS:
        raise HTTPException(status_code=415, detail="Upload an XLSX, XLS, CSV, JSON, or PDF financial file.")

    job_id = str(uuid4())
    workspace = _job_workspace(user.id, job_id)
    job = reserve_job(db, user, "file_upload", workspace)
    job.input_name = filename
    db.commit()
    try:
        workspace.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.exception("Could not allocate private workspace for uploaded job %s.", job.id)
        _update_job(job.id, status="failed", error_code="workspace_unavailable")
        raise HTTPException(status_code=503, detail="Private report storage is temporarily unavailable.")

    input_path = workspace / "client_inbox" / f"source{extension}"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with input_path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    input_path.unlink(missing_ok=True)
                    max_mb = MAX_UPLOAD_BYTES / (1024 * 1024)
                    _update_job(job.id, status="failed", error_code="upload_too_large")
                    raise HTTPException(status_code=413, detail=f"File is larger than the {max_mb:g} MB upload limit.")
                target.write(chunk)
    except OSError:
        logger.exception("Could not save an uploaded file for job %s.", job.id)
        input_path.unlink(missing_ok=True)
        _update_job(job.id, status="failed", error_code="upload_write_failed")
        raise HTTPException(status_code=500, detail="The uploaded file could not be stored.")
    finally:
        await file.close()

    use_celery = bool(os.environ.get("REDIS_URL")) and celery_app is not None
    if use_celery:
        try:
            generate_pack_task.apply_async(
                args=[job.id, user.id, str(input_path)],
                queue="valuation_heavy",
            )
        except Exception as exc:
            logger.warning("Failed to enqueue generate_pack_task via Celery (%s); falling back to background thread.", exc)
            background_tasks.add_task(_run_upload_job_fallback, job.id, user.id, str(input_path))
    else:
        background_tasks.add_task(_run_upload_job_fallback, job.id, user.id, str(input_path))

    return {"job_id": job.id, "status": job.status}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    tenant_id = getattr(user, "tenant_id", None) or getattr(user, "org_id", None) or user.id
    job = get_tenant_job(db, job_id, tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Valuation job not found.")

    result = json.loads(job.result_json) if job.result_json else None
    if result and job.status == "succeeded":
        result.pop("_private_files", None)
        result.pop("_s3_keys", None)
        result["account"] = account_summary(db, user)

    return {
        "job_id": job.id,
        "status": job.status,
        "error": (
            "The valuation could not be completed. Your monthly usage was not charged. Please try again."
            if job.status == "failed"
            else None
        ),
        "result": result,
    }


@router.get("/jobs")
def list_jobs(
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    tenant_id = getattr(user, "tenant_id", None) or getattr(user, "org_id", None) or user.id
    recent_jobs = list_tenant_jobs(db, tenant_id, limit=limit)
    items: list[dict[str, object]] = []
    for job in recent_jobs:
        result = json.loads(job.result_json) if job.result_json else {}
        result.pop("_private_files", None)
        result.pop("_s3_keys", None)
        items.append(
            {
                "job_id": job.id,
                "kind": job.kind,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "company": (result.get("company") or {}).get("name"),
                "files": result.get("files", {}),
            }
        )
    return {"jobs": items}


@router.get("/jobs/{job_id}/files/{file_key}")
def download_job_file(
    job_id: str,
    file_key: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    tenant_id = getattr(user, "tenant_id", None) or getattr(user, "org_id", None) or user.id
    job = get_tenant_job(db, job_id, tenant_id)
    if job is None or job.status != "succeeded":
        raise HTTPException(status_code=404, detail="Report not found.")
    if file_key not in FILE_DETAILS:
        raise HTTPException(status_code=404, detail="Report not found.")

    result = json.loads(job.result_json or "{}")

    # 1. Pre-signed S3/R2 URL redirect when Object Storage is configured
    s3_keys = result.get("_s3_keys") or {}
    s3_key = s3_keys.get(file_key)
    if s3_key and object_store.is_s3_configured():
        try:
            presigned_url = object_store.generate_presigned_url(
                s3_key=s3_key,
                filename=Path(s3_key).name,
                expires_in=900,
                inline=(file_key == "dashboard_html"),
            )
            return RedirectResponse(url=presigned_url, status_code=307)
        except Exception as exc:
            logger.warning("Could not generate pre-signed URL for %s, falling back to local file: %s", s3_key, exc)

    # 2. Local FileResponse fallback
    file_url = (result.get("files") or {}).get(file_key)
    if file_url != f"/api/v1/jobs/{job_id}/files/{file_key}":
        raise HTTPException(status_code=404, detail="Report not found.")

    files = result.get("_private_files") or {}
    file_value = files.get(file_key)
    if not file_value:
        raise HTTPException(status_code=404, detail="Report not found.")
    base = Path(job.workspace_path).resolve()
    path = Path(file_value).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        logger.error("Private report path validation failed for job %s.", job.id)
        raise HTTPException(status_code=404, detail="Report not found.")

    media_type, attachment = FILE_DETAILS[file_key]
    headers = {
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Robots-Tag": "noindex, nofollow",
    }
    if file_key == "dashboard_html":
        headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com data:; "
            "img-src data:; connect-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name if attachment else None,
        headers=headers,
    )
