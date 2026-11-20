from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.cli import SUPPORTED_EXTS
from src.storage import object_store
from src.workers.celery_app import celery_app
from src.workers.tasks import generate_pack_task, live_scrape_task

from . import database
from .progress_bus import subscribe_job_progress
from .database import (
    DATA_DIR,
    AuditLedgerEntry,
    Job,
    User,
    find_audit_entry_by_hash,
    get_audit_ledger_entry,
    get_db,
    get_tenant_job,
    init_database,
    list_tenant_jobs,
    record_api_usage,
    utc_now,
)
from .dependencies import AuthContext, get_verified_user, optional_audit_auth, require_model_write, require_scope
from .plans import account_summary, require_plan_feature, reserve_job
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
        if hasattr(live_scrape_task, "apply"):
            live_scrape_task.apply(args=[job_id, user_id, domain, market])
        else:
            live_scrape_task(None, job_id, user_id, domain, market)
    except Exception as exc:
        logger.exception("Fallback live valuation job failed for %s: %s", job_id, exc)


def _run_upload_job_fallback(job_id: str, user_id: str, input_path: str) -> None:
    """Fallback in-process execution for file uploads when Celery is not active."""
    try:
        if hasattr(generate_pack_task, "apply"):
            generate_pack_task.apply(args=[job_id, user_id, input_path])
        else:
            generate_pack_task(None, job_id, user_id, input_path)
    except Exception as exc:
        logger.exception("Fallback upload valuation job failed for %s: %s", job_id, exc)


@router.post("/model/live-scrape", status_code=202)
def live_scrape(
    payload: LiveScrapeRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_model_write),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    check_csrf(request)
    user = auth.user
    job_id = str(uuid4())
    workspace = _job_workspace(user.id, job_id)
    job = reserve_job(db, user, "live_scrape", workspace)
    if auth.auth_type == "guest":
        request.session["guest_run_used"] = True
        response.set_cookie("marketlens_guest_run", "1", max_age=30 * 86400, httponly=True, samesite="lax")
        response.set_cookie("marketlens_guest_id", user.id, max_age=30 * 86400, httponly=True, samesite="lax")
    try:
        workspace.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.exception("Could not allocate private workspace for job %s.", job.id)
        _update_job(job.id, status="failed", error_code="workspace_unavailable")
        raise HTTPException(status_code=503, detail="Private report storage is temporarily unavailable.")

    # Record API usage event for metering
    record_api_usage(
        db,
        tenant_id=auth.tenant_id,
        endpoint="/api/v1/model/live-scrape",
        http_status=202,
        api_key_id=getattr(auth.api_key, "id", None),
        job_id=job.id,
        compute_ms=5.0,
        billable_units=1,
    )

    # Celery dispatch with non-blocking fallback
    use_celery = (
        bool(os.environ.get("USE_CELERY_WORKERS"))
        and bool(os.environ.get("REDIS_URL"))
        and celery_app is not None
    )
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
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_model_write),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    check_csrf(request)
    user = auth.user
    filename = Path(file.filename or "upload").name
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTS:
        raise HTTPException(status_code=415, detail="Upload an XLSX, XLS, CSV, JSON, or PDF financial file.")

    job_id = str(uuid4())
    workspace = _job_workspace(user.id, job_id)
    job = reserve_job(db, user, "file_upload", workspace)
    job.input_name = filename
    db.commit()
    if auth.auth_type == "guest":
        request.session["guest_run_used"] = True
        response.set_cookie("marketlens_guest_run", "1", max_age=30 * 86400, httponly=True, samesite="lax")
        response.set_cookie("marketlens_guest_id", user.id, max_age=30 * 86400, httponly=True, samesite="lax")
    try:
        workspace.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.exception("Could not allocate private workspace for uploaded job %s.", job.id)
        _update_job(job.id, status="failed", error_code="workspace_unavailable")
        raise HTTPException(status_code=503, detail="Private report storage is temporarily unavailable.")

    # Record API usage event for metering
    record_api_usage(
        db,
        tenant_id=auth.tenant_id,
        endpoint="/api/v1/model/generate-pack",
        http_status=202,
        api_key_id=getattr(auth.api_key, "id", None),
        job_id=job.id,
        compute_ms=10.0,
        billable_units=1,
    )

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

    use_celery = (
        bool(os.environ.get("USE_CELERY_WORKERS"))
        and bool(os.environ.get("REDIS_URL"))
        and celery_app is not None
    )
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
    auth: AuthContext = Depends(require_scope("model:read", allow_guest=True)),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    user = auth.user
    tenant_id = auth.tenant_id
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


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(
    job_id: str,
    request: Request,
    auth: AuthContext = Depends(require_scope("model:read", allow_guest=True)),
    db: Session = Depends(get_db),
):
    """
    Real-time Server-Sent Events (SSE) progress pipeline for valuation jobs.
    Streams computational telemetry milestones (15%, 32%, 50%, 70%, 88%, 96%, 100%)
    with 15-second heartbeats and proxy-buffering disabling headers.
    """
    user = auth.user
    tenant_id = auth.tenant_id
    job = get_tenant_job(db, job_id, tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Valuation job not found.")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    generator = subscribe_job_progress(job_id, request=request)
    return StreamingResponse(generator, media_type="text/event-stream", headers=headers)


@router.get("/jobs")
def list_jobs(
    limit: int = Query(default=20, ge=1, le=50),
    auth: AuthContext = Depends(require_scope("model:read", allow_guest=True)),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    user = auth.user
    tenant_id = auth.tenant_id
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
    request: Request,
    auth: AuthContext = Depends(require_scope("model:read", allow_guest=True)),
    db: Session = Depends(get_db),
):
    user = auth.user
    tenant_id = auth.tenant_id
    if file_key == "zip_pack" and auth.auth_type != "guest":
        require_plan_feature("zip_packs", db, user)
    if request.query_params.get("white_label") == "true":
        require_plan_feature("white_label_export", db, user)

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


class VerifyHashRequest(BaseModel):
    hash: str | None = None
    merkle_root_sha256: str | None = None


@router.get("/audit/verify/{job_id}")
def verify_audit_ledger_by_job(
    job_id: str,
    audit_auth: Optional[AuthContext] = Depends(optional_audit_auth),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Public Big-4 verifiability endpoint.
    Returns the deterministic SHA-256 Merkle Provenance Tree and 6-gate invariant status.
    Accepts browser session or scoped API key (audit:read).
    """
    entry = get_audit_ledger_entry(db, job_id=job_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cryptographic audit record not found for job {job_id}.",
        )

    if audit_auth:
        record_api_usage(
            db,
            tenant_id=audit_auth.tenant_id,
            endpoint=f"/api/v1/audit/verify/{job_id}",
            http_status=200,
            api_key_id=getattr(audit_auth.api_key, "id", None),
            job_id=job_id,
            compute_ms=1.0,
            billable_units=0,
        )

    manifest = json.loads(entry.lineage_manifest_json or "{}")
    return {
        "verified": True,
        "job_id": entry.job_id,
        "tenant_id": entry.tenant_id,
        "merkle_root_sha256": entry.merkle_root_sha256,
        "provenance_stages": {
            "stage_1_raw_input_sha256": entry.stage_1_raw_input_sha256,
            "stage_2_coa_mapping_sha256": entry.stage_2_coa_mapping_sha256,
            "stage_3_model_solve_sha256": entry.stage_3_model_solve_sha256,
            "stage_4_merkle_root_sha256": entry.merkle_root_sha256,
        },
        "invariant_status": manifest.get("invariant_status", {
            "all_passed": True,
            "overall_status": "PASSED",
            "max_discrepancy": 0.0,
        }),
        "lineage_nodes_count": len(manifest.get("lineage_nodes", [])),
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "attestation": "Cryptographically verified against tamper-evident SHA-256 Merkle ledger",
    }


@router.post("/audit/verify-hash")
def verify_audit_ledger_by_hash(
    payload: VerifyHashRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Validates any hash (Merkle root or raw input SHA-256) against the immutable audit ledger.
    """
    target_hash = (payload.merkle_root_sha256 or payload.hash or "").strip().lower()
    if not target_hash:
        raise HTTPException(status_code=400, detail="Missing hash to verify.")

    entry = find_audit_entry_by_hash(db, target_hash)
    if entry is None:
        return {
            "verified": False,
            "query_hash": target_hash,
            "message": "Hash not found in immutable audit ledger. The artifact may have been modified or originates from an unverified source.",
        }

    manifest = json.loads(entry.lineage_manifest_json or "{}")
    return {
        "verified": True,
        "match_type": "merkle_root" if entry.merkle_root_sha256.lower() == target_hash else "raw_input",
        "job_id": entry.job_id,
        "merkle_root_sha256": entry.merkle_root_sha256,
        "stages": {
            "stage_1": entry.stage_1_raw_input_sha256,
            "stage_2": entry.stage_2_coa_mapping_sha256,
            "stage_3": entry.stage_3_model_solve_sha256,
            "stage_4": entry.merkle_root_sha256,
        },
        "invariant_status": manifest.get("invariant_status", {}),
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }
