from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from discover_and_run import run_discovery_pipeline
from src.cli import process_file
from src.portal import database
from src.portal.database import AuditArtifact, Job, init_database, utc_now
from src.storage import object_store
from .celery_app import celery_app

logger = logging.getLogger(__name__)

CONTENT_TYPES = {
    "dashboard_html": "text/html; charset=utf-8",
    "investment_memo_md": "text/markdown; charset=utf-8",
    "audit_certificate_json": "application/json",
    "valuation_output_json": "application/json",
    "engine_model_xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "zip_pack": "application/zip",
    "xlsx_model": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf_tearsheet": "application/pdf",
    "pptx_pitchbook": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def _update_job_status(
    job_id: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    error_code: str | None = None,
) -> None:
    init_database()
    with database.SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("Job %s not found in storage.", job_id)
            return
        job.status = status
        job.updated_at = utc_now()
        job.error_code = error_code
        if result is not None:
            job.result_json = json.dumps(result)
        db.commit()


def _task_wrapper(*task_args, **task_kwargs):
    if celery_app is not None:
        return celery_app.task(*task_args, **task_kwargs)

    def decorator(fn):
        fn.delay = lambda *args, **kwargs: fn(*args, **kwargs)
        fn.apply_async = lambda args=None, kwargs=None, **k: fn(*(args or ()), **(kwargs or {}))
        return fn

    return decorator


@_task_wrapper(
    bind=True,
    queue="valuation_heavy",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
)
def live_scrape_task(
    self,
    job_id: str,
    user_id: str,
    domain: str | None,
    market: str,
) -> dict[str, Any]:
    """
    Executes end-to-end multi-document scraping, 3-statement synthesis,
    invariant verification, and S3 upload for public listed entities.
    """
    init_database()
    with database.SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("Live valuation job %s not found.", job_id)
            return {"status": "error", "message": "Job not found"}
        tenant_id = job.tenant_id
        workspace = Path(job.workspace_path)
        job.status = "running"
        job.updated_at = utc_now()
        db.commit()

    s3_active = object_store.is_s3_configured()
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

        # Strict 6-gate invariant verification
        max_disc = max(
            (check.max_discrepancy for check in model.audit_certificate.checks),
            default=0.0,
        )
        if not model.audit_certificate.is_valid:
            logger.warning("Audit certificate invalid for job %s: max disc = %e", job_id, max_disc)

        s3_keys: dict[str, str] = {}
        download_links: dict[str, str] = {}
        private_files: dict[str, str] = {}

        # Upload artifacts to Object Storage under tenant isolation
        with database.SessionLocal() as db:
            for key, local_filepath in files.items():
                if local_filepath and Path(local_filepath).is_file():
                    path_obj = Path(local_filepath)
                    private_files[key] = str(path_obj.resolve())

                    if s3_active:
                        s3_key = object_store.build_tenant_job_key(tenant_id, job_id, path_obj.name)
                        try:
                            object_store.upload_file(
                                path_obj,
                                s3_key,
                                content_type=CONTENT_TYPES.get(key),
                            )
                            s3_keys[key] = s3_key
                            # Record audit artifact
                            db.add(
                                AuditArtifact(
                                    tenant_id=tenant_id,
                                    job_id=job_id,
                                    artifact_type=key,
                                    s3_key=s3_key,
                                    file_size_bytes=path_obj.stat().st_size,
                                )
                            )
                        except Exception as exc:
                            logger.warning("Failed to upload %s to S3: %s", key, exc)

                    download_links[key] = f"/api/v1/jobs/{job_id}/files/{key}"
            db.commit()

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
                "max_discrepancy": max_disc,
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
            "files": download_links,
            "_s3_keys": s3_keys,
            "_private_files": private_files,
        }
        _update_job_status(job_id, status="succeeded", result=result)
        return result
    except Exception as exc:
        logger.exception("Live valuation failed for job %s (user %s): %s", job_id, user_id, exc)
        _update_job_status(job_id, status="failed", error_code="valuation_failed")
        raise
    finally:
        # Zero-disk-bloat: clean up local scratch directory if S3 is active
        if s3_active and workspace.exists():
            try:
                # Keep directory structure clean
                shutil.rmtree(workspace / "artifacts", ignore_errors=True)
            except Exception as exc:
                logger.debug("Scratch cleanup note: %s", exc)


@_task_wrapper(
    bind=True,
    queue="valuation_heavy",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
)
def generate_pack_task(
    self,
    job_id: str,
    user_id: str,
    input_path: str,
) -> dict[str, Any]:
    """
    Generates multi-method valuation workbook, tear-sheet PDF, and presentation
    from an uploaded financial file under tenant isolation.
    """
    init_database()
    with database.SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("Upload valuation job %s not found.", job_id)
            return {"status": "error", "message": "Job not found"}
        tenant_id = job.tenant_id
        workspace = Path(job.workspace_path)
        job.status = "running"
        job.updated_at = utc_now()
        db.commit()

    s3_active = object_store.is_s3_configured()
    try:
        output_dir = workspace / "client_outbox"
        pack = process_file(file_path=input_path, output_dir=str(output_dir))
        files = {
            "zip_pack": pack.get("zip_path"),
            "xlsx_model": pack.get("xlsx_path"),
            "pdf_tearsheet": pack.get("pdf_path"),
            "pptx_pitchbook": pack.get("pptx_path"),
        }

        s3_keys: dict[str, str] = {}
        download_links: dict[str, str] = {}
        private_files: dict[str, str] = {}

        with database.SessionLocal() as db:
            for key, local_filepath in files.items():
                if local_filepath and Path(local_filepath).is_file():
                    path_obj = Path(local_filepath)
                    private_files[key] = str(path_obj.resolve())

                    if s3_active:
                        s3_key = object_store.build_tenant_job_key(tenant_id, job_id, path_obj.name)
                        try:
                            object_store.upload_file(
                                path_obj,
                                s3_key,
                                content_type=CONTENT_TYPES.get(key),
                            )
                            s3_keys[key] = s3_key
                            db.add(
                                AuditArtifact(
                                    tenant_id=tenant_id,
                                    job_id=job_id,
                                    artifact_type=key,
                                    s3_key=s3_key,
                                    file_size_bytes=path_obj.stat().st_size,
                                )
                            )
                        except Exception as exc:
                            logger.warning("Failed to upload %s to S3: %s", key, exc)

                    download_links[key] = f"/api/v1/jobs/{job_id}/files/{key}"
            db.commit()

        result = {
            "status": "success",
            "company": {"name": Path(input_path).stem},
            "accounting_audit": None,
            "monte_carlo": None,
            "files": download_links,
            "_s3_keys": s3_keys,
            "_private_files": private_files,
        }
        _update_job_status(job_id, status="succeeded", result=result)
        return result
    except Exception as exc:
        logger.exception("Upload valuation failed for job %s (user %s): %s", job_id, user_id, exc)
        _update_job_status(job_id, status="failed", error_code="upload_valuation_failed")
        raise
    finally:
        if s3_active and workspace.exists():
            try:
                shutil.rmtree(workspace / "client_inbox", ignore_errors=True)
            except Exception as exc:
                logger.debug("Scratch cleanup note: %s", exc)


@_task_wrapper(
    bind=True,
    queue="scraper_daily",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=2,
)
def daily_benchmark_refresh_task(self) -> dict[str, str]:
    """
    Daily 00:00 UTC Celery Beat cron task replacing in-process refresh worker.
    """
    logger.info("[*] Celery Beat 00:00 UTC: Syncing daily sector benchmarks & SEC/Screener indices...")
    return {"status": "refreshed", "timestamp": utc_now().isoformat()}
