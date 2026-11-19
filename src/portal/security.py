from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path

from fastapi import HTTPException, Request, Response

from .database import DATA_DIR

SESSION_COOKIE = "marketlens_session"
CSRF_COOKIE = "marketlens_csrf"
PASSWORD_ROUNDS = 310_000


def load_session_secret() -> str:
    configured = os.environ.get("SESSION_SECRET")
    if configured:
        if len(configured) < 32:
            raise RuntimeError("SESSION_SECRET must contain at least 32 characters.")
        return configured

    secret_path = DATA_DIR / "session_secret"
    try:
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(secret_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as secret_file:
            secret_file.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass
    return secret_path.read_text(encoding="utf-8").strip()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ROUNDS)
    return f"pbkdf2_sha256${PASSWORD_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, rounds_text, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        rounds = int(rounds_text)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), rounds)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def new_one_time_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode("utf-8")).hexdigest()


def check_csrf(request: Request) -> None:
    # Scoped API key requests and guest frictionless runs do not require browser CSRF tokens
    auth_header = request.headers.get("authorization", "")
    if request.headers.get("x-api-key") or auth_header.startswith("Bearer ml_live_"):
        return
    if getattr(request.state, "is_guest", False) or request.session.get("is_guest") or request.headers.get("x-guest-run") == "1":
        return
    session_token = request.session.get("csrf_token")
    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get("x-csrf-token")
    if not session_token or not cookie_token or not header_token:
        raise HTTPException(status_code=403, detail="Request verification failed. Refresh the page and try again.")
    if not (
        hmac.compare_digest(session_token, cookie_token)
        and hmac.compare_digest(session_token, header_token)
    ):
        raise HTTPException(status_code=403, detail="Request verification failed. Refresh the page and try again.")


def establish_session(request: Request, response: Response, user_id: str, session_version: int = 0) -> None:
    csrf_token = secrets.token_urlsafe(32)
    request.session.clear()
    request.session["user_id"] = user_id
    request.session["session_version"] = session_version
    request.session["csrf_token"] = csrf_token
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        secure=_secure_cookies(),
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * 14,
    )


def clear_session(request: Request, response: Response) -> None:
    request.session.clear()
    response.delete_cookie(CSRF_COOKIE, path="/", samesite="lax")


def _secure_cookies() -> bool:
    return os.environ.get("APP_ENV") == "production" or bool(os.environ.get("RAILWAY_ENVIRONMENT"))


def email_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
