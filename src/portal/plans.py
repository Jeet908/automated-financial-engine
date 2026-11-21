from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import Job, Subscription, User, get_db, utc_now

_reservation_lock = threading.Lock()

FEATURE_TIERS: dict[str, str] = {
    "standard_valuation": "free",
    "basic_exports": "free",
    "c_suite_pain_points": "free_trial",
    "erp_sync": "pro",
    "api_keys": "pro",
    "zip_packs": "pro",
    "top_quartile_diagnostics": "pro",
    "white_label_export": "business",
    "saml_sso": "business",
    "unlimited_webhooks": "business",
}

PLAN_RANKS: dict[str, int] = {
    "free": 0,
    "free_trial": 1,
    "pro": 2,
    "business": 3,
}


def has_plan_feature(plan_key: str, feature_name: str) -> bool:
    """Returns True if plan_key satisfies the tier requirement for feature_name."""
    min_plan = FEATURE_TIERS.get(feature_name, "pro")
    return PLAN_RANKS.get(plan_key, 0) >= PLAN_RANKS.get(min_plan, 2)


def check_plan_feature(db: Session, user_id: str, feature_name: str) -> None:
    """Raises HTTP 403 JSON detail if the user's plan does not have access to feature_name."""
    plan_key, _ = effective_plan(db, user_id)
    if not has_plan_feature(plan_key, feature_name):
        required_plan = FEATURE_TIERS.get(feature_name, "pro")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "plan_upgrade_required",
                "feature": feature_name,
                "required_plan": required_plan,
                "message": f"Plan upgrade required. Feature '{feature_name}' requires a {required_plan.title()} subscription.",
            },
        )


def require_plan_feature(feature_name: str, db: Session | None = None, user: User | None = None):
    """
    Tier-gating enforcer.
    Usable directly as: require_plan_feature("erp_sync", db, user)
    Or as a FastAPI route dependency: Depends(require_plan_feature("erp_sync"))
    """
    if db is not None and user is not None:
        check_plan_feature(db, user.id, feature_name)
        return None

    def _dependency(
        request: Request,
        db_session: Session = Depends(get_db),
    ) -> User:
        from .dependencies import get_verified_user
        user_obj = get_verified_user(request, db=db_session)
        check_plan_feature(db_session, user_obj.id, feature_name)
        return user_obj

    return _dependency


def plan_catalog() -> dict[str, dict[str, object]]:
    """
    Returns the institutional multi-currency SaaS plan catalog calibrated for ₹2 Crore ARR.
    Prices are stored in INR paise for Razorpay; USD/EUR/GBP shown for global capital allocators.
    """
    return {
        "free": {
            "name": "Executive Sandbox",
            "price_paise": 0,
            "monthly_valuations": int(os.environ.get("FREE_MONTHLY_VALUATIONS", "1")),
            "trial_days": 0,
            "razorpay_plan_env": None,
            "prices": {"USD": 0, "INR": 0, "EUR": 0, "GBP": 0},
            "features": [
                "1 deterministic valuation / month",
                "Real-time listed global ticker scraper",
                "6-gate mathematical invariant proof",
                "Interactive 5×5 sensitivity heatmap",
                "Monte Carlo 10,000-path stochastic bell curve",
                "In-browser interactive HTML5 preview",
            ],
        },
        "pro": {
            "name": "Professional Advisory",
            "price_paise": int(os.environ.get("PRO_PRICE_PAISE", "1499900")),
            "monthly_valuations": int(os.environ.get("PRO_MONTHLY_VALUATIONS", "35")),
            "trial_days": 0,
            "razorpay_plan_env": "RAZORPAY_PLAN_ID_PRO",
            "prices": {"USD": 179, "INR": 14999, "EUR": 165, "GBP": 145},
            "features": [
                "35 full institutional models / month",
                "Live SEC EDGAR, MCA-21 & Companies House sync",
                "Full Excel (.xlsx) live formulas + Vector PDF + PPTX",
                "Operational Pain Point diagnostics & Alpha Prescriptions",
                "Tamper-evident SHA-256 Merkle Audit Certificate export",
                "Priority equity analyst support",
            ],
        },
        "business": {
            "name": "Institutional Fund & PE",
            "price_paise": int(os.environ.get("BUSINESS_PRICE_PAISE", "4999900")),
            "monthly_valuations": int(os.environ.get("BUSINESS_MONTHLY_VALUATIONS", "250")),
            "trial_days": 0,
            "razorpay_plan_env": "RAZORPAY_PLAN_ID_BUSINESS",
            "prices": {"USD": 599, "INR": 49999, "EUR": 549, "GBP": 479},
            "features": [
                "250 institutional valuations & M&A roll-ups / month",
                "1-Click Read-Only ERP Sync (Tally, NetSuite, Zoho, QuickBooks, Xero)",
                "Zero-Touch Monthly Executive Board Packs (.xlsx, .pdf, .pptx)",
                "Scoped VaaS Underwriting API access (metered 5,000 calls/mo)",
                "Multi-region accounting (US GAAP / Ind AS / IFRS / J-GAAP)",
                "Dedicated investment analyst concierge",
            ],
        },
    }


def _subscription_is_current(subscription: Subscription | None) -> bool:
    if subscription is None:
        return False
    status_is_current = subscription.status in {"active", "trialing"}
    cancellation_is_pending = subscription.cancel_at_period_end and subscription.status == "cancelled"
    if not status_is_current and not cancellation_is_pending:
        return False
    end = subscription.current_period_end
    if end is None:
        return False
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return end > datetime.now(timezone.utc)


def effective_plan(db: Session, user_id: str) -> tuple[str, Subscription | None]:
    subscription = db.get(Subscription, user_id)
    if _subscription_is_current(subscription):
        return subscription.plan_key, subscription
    return "free", subscription


def monthly_usage(db: Session, user_id: str) -> int:
    now = utc_now()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(
        db.scalar(
            select(func.count(Job.id)).where(
                Job.user_id == user_id,
                Job.created_at >= period_start,
                Job.status.in_(("pending", "running", "succeeded")),
            )
        )
        or 0
    )


def account_summary(db: Session, user: User) -> dict[str, object]:
    plan_key, subscription = effective_plan(db, user.id)
    plan = plan_catalog().get(plan_key, plan_catalog()["free"])
    used = monthly_usage(db, user.id)
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "email_verified": user.email_verified,
        },
        "plan": {
            "key": plan_key,
            "name": plan["name"],
            "monthly_valuations": plan["monthly_valuations"],
            "used_this_month": used,
            "remaining_this_month": max(0, int(plan["monthly_valuations"]) - used),
        },
        "subscription": (
            {
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "current_period_end": (
                    subscription.current_period_end.isoformat()
                    if subscription.current_period_end
                    else None
                ),
            }
            if subscription
            else None
        ),
    }


def reserve_job(db: Session, user: User, kind: str, workspace_path: Path, job_id: str | None = None) -> Job:
    with _reservation_lock:
        dialect_name = ""
        try:
            dialect_name = getattr(getattr(db.bind, "dialect", None), "name", "")
        except Exception:
            pass

        locked_user = None
        if dialect_name == "postgresql":
            try:
                locked_user = db.scalar(select(User).where(User.id == user.id).with_for_update())
            except Exception as exc:
                try:
                    db.rollback()
                except Exception:
                    pass
                locked_user = db.scalar(select(User).where(User.id == user.id))
        else:
            locked_user = db.scalar(select(User).where(User.id == user.id))

        if locked_user is None:
            locked_user = db.get(User, user.id)
            if locked_user is None:
                if getattr(user, "is_guest", False) or user.id.startswith("guest_"):
                    try:
                        db.merge(user)
                        db.commit()
                        locked_user = db.get(User, user.id)
                    except Exception:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                if locked_user is None:
                    raise HTTPException(status_code=401, detail="Your account is no longer available.")

        plan_key, _ = effective_plan(db, user.id)
        catalog = plan_catalog()
        plan = catalog.get(plan_key, catalog["free"])
        limit = int(plan["monthly_valuations"])
        used = monthly_usage(db, user.id)
        if used >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"You have used your {limit} valuation(s) for this month. Upgrade your plan to continue.",
            )

        tenant_id = getattr(user, "tenant_id", None) or getattr(user, "org_id", None) or user.id
        job = Job(
            id=job_id or str(uuid4()),
            user_id=user.id,
            tenant_id=tenant_id,
            kind=kind,
            status="pending",
            workspace_path=str(workspace_path.resolve()),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
