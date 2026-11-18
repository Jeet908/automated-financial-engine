from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from discover_and_run import run_discovery_pipeline
from src.cli import SUPPORTED_EXTS, process_file

from . import database
from .database import DATA_DIR, Job, User, get_db, init_database, utc_now
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


def _run_live_job(job_id: str, user_id: str, domain: str | None, market: str) -> None:
    init_database()
    with database.SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("Live valuation job %s was not found.", job_id)
            return
        job.status = "running"
        job.updated_at = utc_now()
        workspace = Path(job.workspace_path)
        db.commit()

    try:
        pipeline = run_discovery_pipeline(
            domain=domain,
            market=market,
            quiet=True,
            workspace_root=workspace,
        )
        model = pipeline["engine_a_model"]
        paths = pipeline["paths"]
        files = {
            "dashboard_html": paths["dashboard_html"],
            "investment_memo_md": paths["memo_md"],
            "audit_certificate_json": paths["audit_cert_json"],
            "valuation_output_json": str(workspace / "artifacts" / f"{pipeline['ticker_slug']}_live" / f"{pipeline['ticker_slug']}_valuation_output.json"),
            "engine_model_xlsx": paths["engine_a_xlsx"],
            "zip_pack": paths["pack_zip"],
            "xlsx_model": paths["pack_xlsx"],
            "pdf_tearsheet": paths["pack_pdf"],
            "pptx_pitchbook": paths["pack_pptx"],
        }
        company = pipeline["company"]
        current_price = float(company["current_market_price"])
        fair_value = float(model.value_per_share)
        result = {
            "status": "success",
            "company": {
                "name": company["name"],
                "ticker": company["ticker"],
                "exchange": company["exchange"],
                "industry": company["industry"],
                "currency": company["currency"],
                "current_market_price": current_price,
                "fair_value_per_share": round(fair_value, 2),
                "upside_pct": round((fair_value / current_price - 1) * 100, 2) if current_price > 0 else 0,
                "wacc": round(model.wacc * 100, 2),
                "enterprise_value": round(model.enterprise_value, 2),
                "equity_value": round(model.equity_value, 2),
            },
            "accounting_audit": {
                "overall_status": model.audit_certificate.overall_status,
                "is_valid": model.audit_certificate.is_valid,
                "max_discrepancy": max(
                    (check.max_discrepancy for check in model.audit_certificate.checks),
                    default=0.0,
                ),
                "checks": [
                    {
                        "name": check.name,
                        "passed": check.passed,
                        "max_discrepancy": check.max_discrepancy,
                    }
                    for check in model.audit_certificate.checks
                ],
            },
            "pain_points": getattr(model, "pain_points", None),
            "monte_carlo": {
                "iterations": model.monte_carlo.iterations,
                "median_price": model.monte_carlo.median_price,
                "prob_undervalued": model.monte_carlo.prob_undervalued,
            },
            "files": {
                key: f"/api/v1/jobs/{job_id}/files/{key}"
                for key, path in files.items()
                if path and Path(path).is_file()
            },
            "_private_files": {
                key: str(Path(path).resolve())
                for key, path in files.items()
                if path and Path(path).is_file()
            },
        }
        _update_job(job_id, status="succeeded", result=result)
    except Exception:
        logger.exception("Live valuation failed for job %s (user %s).", job_id, user_id)
        _update_job(job_id, status="failed", error_code="valuation_failed")


def _run_upload_job(job_id: str, user_id: str, input_path: str) -> None:
    init_database()
    with database.SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("Upload valuation job %s was not found.", job_id)
            return
        job.status = "running"
        job.updated_at = utc_now()
        workspace = Path(job.workspace_path)
        db.commit()

    try:
        output_dir = workspace / "client_outbox"
        pack = process_file(file_path=input_path, output_dir=str(output_dir))
        files = {
            "zip_pack": pack.get("zip_path"),
            "xlsx_model": pack.get("xlsx_path"),
            "pdf_tearsheet": pack.get("pdf_path"),
            "pptx_pitchbook": pack.get("pptx_path"),
        }
        result = {
            "status": "success",
            "company": {"name": job.input_name or Path(input_path).stem},
            "accounting_audit": None,
            "monte_carlo": None,
            "files": {
                key: f"/api/v1/jobs/{job_id}/files/{key}"
                for key, path in files.items()
                if path and Path(path).is_file()
            },
            "_private_files": {
                key: str(Path(path).resolve())
                for key, path in files.items()
                if path and Path(path).is_file()
            },
        }
        _update_job(job_id, status="succeeded", result=result)
    except Exception:
        logger.exception("Uploaded-file valuation failed for job %s (user %s).", job_id, user_id)
        _update_job(job_id, status="failed", error_code="upload_valuation_failed")


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
    background_tasks.add_task(_run_live_job, job.id, user.id, payload.domain, payload.market)
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

    background_tasks.add_task(_run_upload_job, job.id, user.id, str(input_path))
    return {"job_id": job.id, "status": job.status}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Valuation job not found.")
    result = json.loads(job.result_json) if job.result_json else None
    if result and job.status == "succeeded":
        result.pop("_private_files", None)
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
    recent_jobs = (
        db.query(Job)
        .filter(Job.user_id == user.id)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .all()
    )
    items: list[dict[str, object]] = []
    for job in recent_jobs:
        result = json.loads(job.result_json) if job.result_json else {}
        result.pop("_private_files", None)
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
    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id or job.status != "succeeded":
        raise HTTPException(status_code=404, detail="Report not found.")
    if file_key not in FILE_DETAILS:
        raise HTTPException(status_code=404, detail="Report not found.")
    result = json.loads(job.result_json or "{}")
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
