"""
Scoped API Key Management & Metered VaaS Endpoints.
Allows institutional clients to create, manage, revoke API keys and monitor metered usage.
"""
from __future__ import annotations

import json
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import (
    create_api_key,
    get_db,
    get_tenant_api_key,
    get_tenant_api_usage_summary,
    list_tenant_api_keys,
    record_api_usage,
    revoke_tenant_api_key,
)
from .dependencies import AuthContext, authenticate_request
from .plans import account_summary, require_plan_feature
from .security import check_csrf

router = APIRouter(prefix="/api/v1/keys", tags=["api_keys"])


class CreateKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    scopes: List[str] = Field(default_factory=lambda: ["model:write", "diagnostics:read", "audit:read"])
    rate_limit_per_min: int = Field(default=60, ge=1, le=1200)


@router.post("", status_code=201)
def create_key(
    payload: CreateKeyRequest,
    request: Request,
    auth: AuthContext = Depends(authenticate_request),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Creates a new scoped API key for the tenant and returns the one-time raw secret.
    The secret is hashed deterministically using SHA-256 and never stored in plaintext.
    """
    if auth.auth_type == "session":
        check_csrf(request)
    require_plan_feature("api_keys", db, auth.user)
    record, secret_key = create_api_key(
        session=db,
        tenant_id=auth.tenant_id,
        name=payload.name.strip(),
        scopes=payload.scopes,
        rate_limit_per_min=payload.rate_limit_per_min,
    )

    # Metering event
    record_api_usage(
        db,
        tenant_id=auth.tenant_id,
        endpoint="/api/v1/keys",
        http_status=201,
        api_key_id=getattr(auth.api_key, "id", None),
        compute_ms=1.5,
        billable_units=0,
    )

    return {
        "id": record.id,
        "tenant_id": record.tenant_id,
        "name": record.name,
        "key_prefix": record.key_prefix,
        "secret_key": secret_key,
        "scopes": payload.scopes,
        "rate_limit_per_min": record.rate_limit_per_min,
        "created_at": record.created_at.isoformat(),
        "warning": "Copy and store this secret key now. You will not be able to see it again.",
    }


@router.get("")
def list_keys(
    auth: AuthContext = Depends(authenticate_request),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Lists active and revoked API keys (showing only masked prefixes) for the tenant.
    """
    keys = list_tenant_api_keys(db, auth.tenant_id)
    summary = get_tenant_api_usage_summary(db, auth.tenant_id)

    formatted_keys = [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scopes": json.loads(k.scopes or "[]"),
            "rate_limit_per_min": k.rate_limit_per_min,
            "status": "revoked" if k.revoked_at else "active",
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat(),
        }
        for k in keys
    ]

    return {
        "keys": formatted_keys,
        "usage_summary": summary,
    }


@router.delete("/{key_id}")
def revoke_key(
    key_id: str,
    request: Request,
    auth: AuthContext = Depends(authenticate_request),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Immediately revokes an API key, blocking subsequent authenticated requests.
    """
    if auth.auth_type == "session":
        check_csrf(request)
    revoked = revoke_tenant_api_key(db, key_id, auth.tenant_id)
    if not revoked:
        raise HTTPException(
            status_code=404,
            detail="API key not found or already revoked.",
        )

    return {
        "revoked": True,
        "key_id": key_id,
        "status": "revoked",
    }


@router.get("/usage")
def get_usage(
    auth: AuthContext = Depends(authenticate_request),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns monthly metered billable units, remaining plan quota, and endpoint latency breakdown.
    """
    summary = get_tenant_api_usage_summary(db, auth.tenant_id)
    acct = account_summary(db, auth.user)

    plan_limit = acct.get("monthly_valuations", 100)
    used_units = summary.get("total_billable_units", 0)
    remaining = max(0, plan_limit - used_units)

    return {
        "tenant_id": auth.tenant_id,
        "plan_key": acct.get("plan_key", "pro"),
        "plan_limit": plan_limit,
        "total_billable_units": used_units,
        "remaining_quota": remaining,
        "usage_summary": summary,
    }
