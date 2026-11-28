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
    "c_suite_pain_points": "pro",
    "erp_sync": "business",
    "api_keys": "business",
    "zip_packs": "pro",
    "top_quartile_diagnostics": "pro",
    "white_label_export": "enterprise",
    "saml_sso": "enterprise",
    "unlimited_webhooks": "enterprise",
}

PLAN_RANKS: dict[str, int] = {
    "free": 0,
    "free_trial": 0,
    "pro": 1,
    "business": 2,
    "enterprise": 3,
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
            "name": "Executive Pilot",
            "price_paise": 0,
            "monthly_valuations": int(os.environ.get("FREE_MONTHLY_VALUATIONS", "1")),
            "trial_days": 0,
            "razorpay_plan_env": None,
            "prices": {"USD": 0, "INR": 0, "EUR": 0, "GBP": 0},
            "features": [
                "1 full institutional benchmark model",
                "Real-time listed global ticker scraper (US/India/UK)",
                "6-gate mathematical invariant verification (0.00 err)",
                "Interactive 5×5 sensitivity heatmap solver",
                "10,000-path Monte Carlo distribution & DuPont diagnostic",
                "In-browser interactive report preview",
            ],
        },
        "pro": {
            "name": "Advisory & Corporate Desk",
            "price_paise": int(os.environ.get("PRO_PRICE_PAISE", "3999900")),
            "monthly_valuations": int(os.environ.get("PRO_MONTHLY_VALUATIONS", "25")),
            "trial_days": 0,
            "razorpay_plan_env": "RAZORPAY_PLAN_ID_PRO",
            "prices": {"USD": 499, "INR": 39999, "EUR": 449, "GBP": 399},
            "features": [
                "25 full institutional valuation models / month",
                "Complete editable Excel (.xlsx) live formulas + Vector PDF + PPTX",
                "C-Suite Operational Diagnostics & Variance Sensitivity Analysis",
                "Tamper-evident SHA-256 Merkle Audit Certificate export",
                "Multi-region accounting (US GAAP / Ind AS / IFRS)",
                "Priority quant & model engineering support",
            ],
        },
        "business": {
            "name": "Private Equity & Fund Desk",
            "price_paise": int(os.environ.get("BUSINESS_PRICE_PAISE", "11999900")),
            "monthly_valuations": int(os.environ.get("BUSINESS_MONTHLY_VALUATIONS", "100")),
            "trial_days": 0,
            "razorpay_plan_env": "RAZORPAY_PLAN_ID_BUSINESS",
            "prices": {"USD": 1499, "INR": 119999, "EUR": 1399, "GBP": 1199},
            "features": [
                "100 institutional valuations & M&A roll-ups / month",
                "Dedicated ERP Ingestion Pipeline (NetSuite, Tally, Zoho, QBO)",
                "Zero-Touch Monthly Executive Board Packs (.xlsx, .pdf, .pptx)",
                "10,000-Path Monte Carlo Simulation & 95% Parametric VaR Distribution",
                "Automated SEC EDGAR, MCA-21 & Companies House sync",
                "Dynamic Sector Peer Comps (Semiconductors, Cloud SaaS, Defence)",
            ],
        },
        "enterprise": {
            "name": "Institutional Sovereign",
            "price_paise": int(os.environ.get("ENTERPRISE_PRICE_PAISE", "39999900")),
            "monthly_valuations": int(os.environ.get("ENTERPRISE_MONTHLY_VALUATIONS", "999")),
            "trial_days": 0,
            "razorpay_plan_env": "RAZORPAY_PLAN_ID_ENTERPRISE",
            "prices": {"USD": 4999, "INR": 399999, "EUR": 4599, "GBP": 3999},
            "features": [
                "Unlimited institutional valuations & continuous model roll-forwards",
                "Zero-Touch Monthly Executive Board Packs across all subsidiaries",
                "Dedicated Private Cloud VPC / On-Premise Deployment",
                "Scoped VaaS Underwriting API access (metered 50,000 calls/mo)",
                "Big-4 Accounting Invariant Audit Defense & Attestation",
                "24/7 Dedicated Quant & Principal Valuation Concierge",
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
