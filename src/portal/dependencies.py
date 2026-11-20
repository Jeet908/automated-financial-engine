from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import APIKey, APIUsageEvent, User, get_api_key_by_hash, get_db, record_api_usage, utc_now

_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMIT_WINDOWS: dict[str, list[float]] = {}


@dataclass
class AuthContext:
    user: User
    tenant_id: str
    auth_type: str  # "session" | "api_key"
    api_key: Optional[APIKey] = None
    scopes: List[str] = field(default_factory=list)


def _extract_raw_api_key(request: Request) -> Optional[str]:
    raw_key = request.headers.get("x-api-key")
    if raw_key:
        return raw_key.strip()
    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token.startswith("ml_live_"):
            return token
    return None


def _check_api_key_rate_limit(key_id: str, max_per_min: int) -> None:
    now = time.time()
    cutoff = now - 60.0
    with _RATE_LIMIT_LOCK:
        history = _RATE_LIMIT_WINDOWS.setdefault(key_id, [])
        # Prune older than 60s
        history = [ts for ts in history if ts >= cutoff]
        if len(history) >= max_per_min:
            _RATE_LIMIT_WINDOWS[key_id] = history
            raise HTTPException(
                status_code=429,
                detail=f"API rate limit exceeded ({max_per_min} req/min). Please back off and retry.",
            )
        history.append(now)
        _RATE_LIMIT_WINDOWS[key_id] = history


def authenticate_request(
    request: Request,
    db: Session = Depends(get_db),
    required_scope: Optional[str] = None,
    allow_guest: bool = False,
) -> AuthContext:
    """
    Dual-mode authentication dependency:
    Accepts an active API Key (X-API-Key / Authorization: Bearer ml_live_...),
    a verified browser session, or 1-run guest access if allow_guest=True.
    """
    raw_key = _extract_raw_api_key(request)

    if raw_key:
        # Validate API Key
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        api_key = get_api_key_by_hash(db, key_hash)
        if api_key is None or api_key.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key.")

        # Scope enforcement
        key_scopes = json.loads(api_key.scopes or "[]")
        if required_scope and (required_scope not in key_scopes and "*" not in key_scopes):
            raise HTTPException(
                status_code=403,
                detail=f"API key lacks required scope '{required_scope}'. Granted: {key_scopes}",
            )

        # Sliding window rate limit check
        _check_api_key_rate_limit(api_key.id, api_key.rate_limit_per_min)

        # Update last used timestamp
        api_key.last_used_at = utc_now()
        db.commit()

        # Resolve associated User or synthesize tenant service user
        tenant_id = api_key.tenant_id
        user = db.query(User).filter(User.org_id == tenant_id).first() or db.query(User).filter(User.id == tenant_id).first()
        if user is None:
            user = User(
                id=tenant_id,
                email=f"api_{tenant_id[:8]}@enterprise.internal",
                org_id=tenant_id,
                email_verified=True,
            )
        setattr(user, "tenant_id", tenant_id)

        auth_ctx = AuthContext(
            user=user,
            tenant_id=tenant_id,
            auth_type="api_key",
            api_key=api_key,
            scopes=key_scopes,
        )
        setattr(request.state, "auth_context", auth_ctx)
        return auth_ctx

    # Fallback to session cookie
    user_id = request.session.get("user_id")
    if user_id:
        user = db.get(User, user_id)
        if user is not None:
            if request.session.get("is_guest"):
                tenant_id = user.id
                setattr(user, "tenant_id", tenant_id)
                setattr(user, "is_guest", True)
                auth_ctx = AuthContext(
                    user=user,
                    tenant_id=tenant_id,
                    auth_type="guest",
                    api_key=None,
                    scopes=["model:write", "model:read"],
                )
                setattr(request.state, "auth_context", auth_ctx)
                setattr(request.state, "is_guest", True)
                return auth_ctx

            if request.session.get("session_version") != user.session_version:
                request.session.clear()
                raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
            if not user.email_verified:
                raise HTTPException(status_code=403, detail="Verify your email address before using valuations.")

            tenant_id = getattr(user, "org_id", None) or user.id
            setattr(user, "tenant_id", tenant_id)

            auth_ctx = AuthContext(
                user=user,
                tenant_id=tenant_id,
                auth_type="session",
                api_key=None,
                scopes=["*"],
            )
            setattr(request.state, "auth_context", auth_ctx)
            return auth_ctx

    # Unauthenticated path: check for 1-run frictionless guest allowance
    if allow_guest:
        guest_run_used = (
            request.cookies.get("marketlens_guest_run") == "1"
            or bool(request.session.get("guest_run_used"))
        )
        if guest_run_used and required_scope == "model:write":
            raise HTTPException(
                status_code=401,
                detail="Guest valuation limit reached (1 run). Sign up for a 14-day free trial or sign in to continue.",
            )

        # Synthesize persistent guest user for trial run
        guest_id = request.cookies.get("marketlens_guest_id") or f"guest_{secrets.token_hex(8)}"
        guest_user = db.get(User, guest_id)
        if not guest_user:
            guest_user = User(
                id=guest_id,
                email=f"{guest_id}@guest.marketlens.local",
                org_id=guest_id,
                email_verified=True,
                terms_accepted_at=utc_now(),
                session_version=1,
            )
            db.add(guest_user)
            db.commit()
            db.refresh(guest_user)

        setattr(guest_user, "tenant_id", guest_id)
        setattr(guest_user, "is_guest", True)
        request.session["user_id"] = guest_id
        request.session["session_version"] = guest_user.session_version
        request.session["is_guest"] = True
        if not request.session.get("csrf_token"):
            request.session["csrf_token"] = secrets.token_urlsafe(32)

        auth_ctx = AuthContext(
            user=guest_user,
            tenant_id=guest_id,
            auth_type="guest",
            api_key=None,
            scopes=["model:write", "model:read"],
        )
        setattr(request.state, "auth_context", auth_ctx)
        setattr(request.state, "is_guest", True)
        return auth_ctx

    raise HTTPException(status_code=401, detail="Sign in to continue or provide an X-API-Key.")


def require_scope(scope: str, allow_guest: bool = False) -> Callable:
    """Dependency factory that validates a required scope when using API keys."""
    def _scope_dependency(request: Request, db: Session = Depends(get_db)) -> AuthContext:
        return authenticate_request(request, db=db, required_scope=scope, allow_guest=allow_guest)
    return _scope_dependency


require_model_write = require_scope("model:write", allow_guest=True)
require_diagnostics_read = require_scope("diagnostics:read")
require_audit_read = require_scope("audit:read")


def optional_audit_auth(request: Request, db: Session = Depends(get_db)) -> Optional[AuthContext]:
    """Validates API key and 'audit:read' scope if API key header is supplied."""
    raw_key = _extract_raw_api_key(request)
    if raw_key:
        return authenticate_request(request, db=db, required_scope="audit:read")
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_ctx = authenticate_request(request, db=db)
    return auth_ctx.user


def get_verified_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_ctx = authenticate_request(request, db=db)
    return auth_ctx.user
