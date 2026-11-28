from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import EmailToken, FailedLoginAttempt, Subscription, User, get_db, utc_now
from .dependencies import get_current_user
from .mailer import email_delivery_configured, send_email
from .plans import account_summary
from .security import (
    check_csrf,
    clear_session,
    email_token_hash,
    establish_session,
    hash_password,
    load_session_secret,
    new_one_time_token,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(24))


def _email_digest(email: str) -> str:
    return hmac.new(
        load_session_secret().encode("utf-8"),
        email.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _check_login_rate(db: Session, email: str) -> str:
    digest = _email_digest(email)
    recent_attempts = db.scalar(
        select(func.count(FailedLoginAttempt.id)).where(
            FailedLoginAttempt.email_digest == digest,
            FailedLoginAttempt.attempted_at >= utc_now() - timedelta(minutes=15),
        )
    ) or 0
    if recent_attempts >= 10:
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in 15 minutes.")
    return digest


class Credentials(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=12, max_length=256)
    accepted_terms: bool = False


class ResetRequest(BaseModel):
    email: str = Field(max_length=320)


class TokenRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)


class PasswordReset(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    password: str = Field(min_length=12, max_length=256)


def _public_base_url(request: Request) -> str:
    configured = os.environ.get("PUBLIC_APP_URL")
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if configured:
        return configured.rstrip("/")
    if railway_domain:
        return f"https://{railway_domain}".rstrip("/")
    if os.environ.get("APP_ENV") == "production" or os.environ.get("RAILWAY_ENVIRONMENT"):
        raise HTTPException(status_code=503, detail="The public application URL is not configured.")
    return str(request.base_url).rstrip("/")


def _new_email_token(db: Session, user: User, purpose: str) -> str:
    token, token_hash = new_one_time_token()
    db.add(
        EmailToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=utc_now() + timedelta(hours=24),
        )
    )
    return token


def _token_is_expired(token: EmailToken) -> bool:
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=utc_now().tzinfo)
    return expires_at <= utc_now()


def _send_token_email(request: Request, user: User, token: str, purpose: str) -> None:
    if purpose == "verify_email":
        subject = "Verify your MarketLens email"
        link = f"{_public_base_url(request)}/?verify_email={token}"
        body = f"Confirm your email address using this link. It expires in 24 hours:\n\n{link}\n"
    else:
        subject = "Reset your MarketLens password"
        link = f"{_public_base_url(request)}/?reset_password={token}"
        body = f"Reset your password using this link. It expires in 24 hours:\n\n{link}\n"
    send_email(user.email, subject, body)


@router.post("/register", status_code=202)
def register(
    payload: Credentials,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if not payload.accepted_terms:
        raise HTTPException(status_code=422, detail="Accept the Terms and Privacy Notice to create an account.")

    # Seamless instant onboarding when SMTP email delivery is not configured
    if not email_delivery_configured():
        existing_user = db.scalar(select(User).where(User.email == email))
        if existing_user:
            raise HTTPException(status_code=409, detail="An account with this email already exists. Please sign in.")
        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            email_verified=True,
            terms_accepted_at=utc_now(),
            terms_version=os.environ.get("TERMS_VERSION", "2026-11"),
        )
        db.add(user)
        db.flush()
        db.add(
            Subscription(
                user_id=user.id,
                tenant_id=user.tenant_id,
                provider="trial",
                plan_key="pro",
                status="active",
                current_period_end=utc_now() + timedelta(days=30),
                cancel_at_period_end=False,
            )
        )
        db.commit()
        establish_session(request, response, user.id, user.session_version)
        summary = account_summary(db, user)
        summary["csrf_token"] = request.session["csrf_token"]
        summary["status"] = "accepted"
        summary["message"] = "Account created and signed in successfully. Welcome to MarketLens!"
        return summary

    _public_base_url(request)
    if db.scalar(select(User).where(User.email == email)):
        return {"status": "accepted", "message": "If that address can be registered, verification instructions will be sent."}

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        email_verified=False,
        terms_accepted_at=utc_now(),
        terms_version=os.environ.get("TERMS_VERSION", "2026-11"),
    )
    db.add(user)
    db.flush()
    token = _new_email_token(db, user, "verify_email")
    db.commit()
    try:
        _send_token_email(request, user, token, "verify_email")
    except (OSError, RuntimeError):
        logger.exception("Verification message delivery failed.")
        db.query(EmailToken).filter(EmailToken.user_id == user.id).delete()
        db.delete(user)
        db.commit()
        raise HTTPException(status_code=503, detail="We could not send the verification email. Please try again.")
    return {"status": "accepted", "message": "If that address can be registered, verification instructions will be sent."}


@router.post("/login")
def login(
    payload: Credentials,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    email = payload.email.strip().lower()
    email_digest = _check_login_rate(db, email)
    user = db.scalar(select(User).where(User.email == email))
    password_ok = verify_password(payload.password, user.password_hash if user else _DUMMY_PASSWORD_HASH)
    if user is None or not password_ok:
        db.add(FailedLoginAttempt(email_digest=email_digest))
        db.commit()
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    db.query(FailedLoginAttempt).filter(FailedLoginAttempt.email_digest == email_digest).delete()
    if not user.email_verified:
        if not email_delivery_configured():
            user.email_verified = True
            db.commit()
        else:
            raise HTTPException(status_code=403, detail="Verify your email address before signing in.")
    establish_session(request, response, user.id, user.session_version)
    summary = account_summary(db, user)
    summary["csrf_token"] = request.session["csrf_token"]
    return summary


@router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    check_csrf(request)
    clear_session(request, response)
    return {"status": "signed_out"}


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)) -> dict[str, object]:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if user is None:
        return {"user": None}
    summary = account_summary(db, user)
    summary["csrf_token"] = request.session.get("csrf_token")
    return summary


@router.post("/verify-email")
def verify_email(payload: TokenRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    token_row = db.scalar(
        select(EmailToken).where(
            EmailToken.token_hash == email_token_hash(payload.token),
            EmailToken.purpose == "verify_email",
            EmailToken.used_at.is_(None),
        )
    )
    if token_row is None or _token_is_expired(token_row):
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired.")
    user = db.get(User, token_row.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="This verification link is no longer valid.")
    user.email_verified = True
    token_row.used_at = utc_now()
    existing_sub = db.get(Subscription, user.id)
    if existing_sub is None:
        db.add(
            Subscription(
                user_id=user.id,
                tenant_id=user.tenant_id,
                provider="trial",
                plan_key="free_trial",
                status="trialing",
                current_period_end=utc_now() + timedelta(days=14),
                cancel_at_period_end=False,
            )
        )
    db.commit()
    return {"status": "verified", "message": "Email verified with 14-Day Free Trial activated. You can now sign in."}


@router.post("/verification/resend", status_code=202)
def resend_verification(
    payload: ResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not email_delivery_configured():
        raise HTTPException(status_code=503, detail="Email delivery is not configured yet.")
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email, User.email_verified.is_(False)))
    if user:
        token = _new_email_token(db, user, "verify_email")
        db.commit()
        try:
            _send_token_email(request, user, token, "verify_email")
        except (OSError, RuntimeError):
            logger.exception("Verification message delivery failed.")
            raise HTTPException(status_code=503, detail="We could not send the verification email. Please try again.")
    return {"status": "accepted", "message": "If that account needs verification, a link has been sent."}


@router.post("/password/forgot", status_code=202)
def forgot_password(
    payload: ResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not email_delivery_configured():
        raise HTTPException(status_code=503, detail="Password recovery email is not configured yet.")
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user and user.password_hash:
        token = _new_email_token(db, user, "reset_password")
        db.commit()
        try:
            _send_token_email(request, user, token, "reset_password")
        except (OSError, RuntimeError):
            logger.exception("Password reset message delivery failed.")
            raise HTTPException(status_code=503, detail="We could not send the password reset email. Please try again.")
    return {"status": "accepted", "message": "If the account is eligible, a reset link has been sent."}


@router.post("/password/reset")
def reset_password(payload: PasswordReset, db: Session = Depends(get_db)) -> dict[str, str]:
    token_row = db.scalar(
        select(EmailToken).where(
            EmailToken.token_hash == email_token_hash(payload.token),
            EmailToken.purpose == "reset_password",
            EmailToken.used_at.is_(None),
        )
    )
    if token_row is None or _token_is_expired(token_row):
        raise HTTPException(status_code=400, detail="This password reset link is invalid or expired.")
    user = db.get(User, token_row.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="This password reset link is no longer valid.")
    user.password_hash = hash_password(payload.password)
    user.session_version += 1
    token_row.used_at = utc_now()
    db.commit()
    return {"status": "password_updated", "message": "Password updated. Sign in with your new password."}


@router.get("/google/start")
def google_start(request: Request, terms_accepted: bool = False):
    if not terms_accepted:
        raise HTTPException(status_code=422, detail="Accept the Terms and Privacy Notice before using Google sign-in.")
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet.")
    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state
    request.session["google_terms_accepted"] = True
    redirect_uri = f"{_public_base_url(request)}/api/v1/auth/google/callback"
    params = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}", status_code=302)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    expected_state = request.session.pop("google_oauth_state", None)
    terms_accepted = request.session.pop("google_terms_accepted", False)
    if not expected_state or not secrets.compare_digest(expected_state, state) or not terms_accepted:
        raise HTTPException(status_code=400, detail="Google sign-in state is invalid. Please try again.")

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet.")
    redirect_uri = f"{_public_base_url(request)}/api/v1/auth/google/callback"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise HTTPException(status_code=502, detail="Google did not return an access token.")
            profile_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
    except httpx.HTTPError:
        logger.exception("Google sign-in request failed.")
        raise HTTPException(status_code=502, detail="Google sign-in could not be completed. Please try again.")

    email = str(profile.get("email", "")).strip().lower()
    subject = str(profile.get("sub", "")).strip()
    email_verified = profile.get("email_verified") is True or str(profile.get("email_verified")).lower() == "true"
    if not email or not subject or not email_verified or not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=403, detail="Google did not provide a verified email address.")

    user = db.scalar(select(User).where(User.google_subject == subject))
    if user is None:
        user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            google_subject=subject,
            email_verified=True,
            terms_accepted_at=utc_now(),
            terms_version=os.environ.get("TERMS_VERSION", "2026-11"),
        )
        db.add(user)
    else:
        if user.email != email:
            raise HTTPException(status_code=409, detail="This Google account is linked to a different email address.")
        user.google_subject = subject
        user.email_verified = True
        if user.terms_accepted_at is None:
            user.terms_accepted_at = utc_now()
            user.terms_version = os.environ.get("TERMS_VERSION", "2026-11")
    db.flush()
    existing_sub = db.get(Subscription, user.id)
    if existing_sub is None:
        db.add(
            Subscription(
                user_id=user.id,
                tenant_id=user.tenant_id,
                provider="trial",
                plan_key="free_trial",
                status="trialing",
                current_period_end=utc_now() + timedelta(days=14),
                cancel_at_period_end=False,
            )
        )
    db.commit()
    response = RedirectResponse("/", status_code=303)
    establish_session(request, response, user.id, user.session_version)
    return response


class GuestTrialRequest(BaseModel):
    email: str = Field(..., max_length=320)


@router.post("/trial/guest-activate")
def guest_activate_trial(
    payload: GuestTrialRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Frictionless 1-click Free Trial activation:
    Instantly provisions/upgrades user with 14-day Free Trial (5 full valuations),
    sets authenticated session cookie, and lifts guest rate-limit with zero email delay.
    """
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(16)),
            email_verified=True,
            terms_accepted_at=utc_now(),
            terms_version=os.environ.get("TERMS_VERSION", "2026-11"),
        )
        db.add(user)
        db.flush()
    else:
        # Security: Prevent account takeover — existing users must authenticate via password
        raise HTTPException(
            status_code=409,
            detail="An account with this email address already exists. Please sign in with your credentials.",
        )

    existing_sub = db.get(Subscription, user.id)
    if not existing_sub:
        db.add(
            Subscription(
                user_id=user.id,
                tenant_id=user.tenant_id,
                provider="trial",
                plan_key="free_trial",
                status="trialing",
                current_period_end=utc_now() + timedelta(days=14),
                cancel_at_period_end=False,
            )
        )
    elif existing_sub.plan_key == "free":
        existing_sub.plan_key = "free_trial"
        existing_sub.status = "trialing"
        existing_sub.current_period_end = utc_now() + timedelta(days=14)
    db.commit()

    response.delete_cookie("marketlens_guest_run", path="/")
    establish_session(request, response, user.id, user.session_version)
    summary = account_summary(db, user)
    summary["csrf_token"] = request.session["csrf_token"]
    return {
        "status": "trial_activated",
        "message": "14-Day Free Trial activated! 5 valuation credits added.",
        "account": summary,
        "csrf_token": request.session["csrf_token"],
    }


@router.post("/trial/activate")
def activate_trial(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    check_csrf(request)
    existing_sub = db.get(Subscription, user.id)
    if existing_sub and existing_sub.status in ("active", "trialing") and existing_sub.plan_key != "free":
        return {"status": "active", "message": f"Already active on {existing_sub.plan_key}."}
    if existing_sub:
        existing_sub.plan_key = "free_trial"
        existing_sub.status = "trialing"
        existing_sub.current_period_end = utc_now() + timedelta(days=14)
        existing_sub.cancel_at_period_end = False
    else:
        db.add(
            Subscription(
                user_id=user.id,
                tenant_id=user.tenant_id,
                provider="trial",
                plan_key="free_trial",
                status="trialing",
                current_period_end=utc_now() + timedelta(days=14),
                cancel_at_period_end=False,
            )
        )
    db.commit()
    return {"status": "trial_activated", "message": "14-Day Free Trial activated with full executive access!"}
