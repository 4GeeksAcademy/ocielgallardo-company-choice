import hashlib
import json
import logging
import os
import secrets
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import certifi
from dotenv import load_dotenv
from fastapi import HTTPException
from tinydb import Query

from services.app.core.database import password_reset_tokens_table, users_table
from services.app.core.security import hash_password, verify_password

# Load root .env regardless of import order / working directory.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ROOT_ENV)

logger = logging.getLogger(__name__)

_GENERIC_EMAIL_FAILURE = "Unable to send email. Please try again later."


def _ssl_context() -> ssl.SSLContext:
    """
    Prefer certifi CA bundle. On some Windows/proxy setups verification still
    fails; set EMAIL_SSL_VERIFY=false for local development only.
    """
    verify = os.getenv("EMAIL_SSL_VERIFY", "true").strip().lower() not in (
        "0",
        "false",
        "no",
    )
    if not verify:
        logger.warning(
            "EMAIL_SSL_VERIFY is disabled; TLS certificate verification skipped for email."
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context(cafile=certifi.where())


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _token_expire_minutes() -> int:
    raw = os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30")
    try:
        minutes = int(raw)
    except (TypeError, ValueError):
        logger.error("Invalid PASSWORD_RESET_TOKEN_EXPIRE_MINUTES value.")
        raise HTTPException(
            status_code=500,
            detail=_GENERIC_EMAIL_FAILURE,
        ) from None
    if minutes <= 0:
        logger.error("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES must be positive.")
        raise HTTPException(
            status_code=500,
            detail=_GENERIC_EMAIL_FAILURE,
        )
    return minutes


def create_password_reset_token(user_id: int) -> str:
    """
    Creates a short-lived, single-use reset token and stores its state server-side.
    Invalidates any previous unused tokens for the same user.
    """
    query = Query()
    password_reset_tokens_table.remove(query.user_id == user_id)

    token = secrets.token_urlsafe(32)
    token_hash = _sha256(token)
    expires_at = _now_utc() + timedelta(minutes=_token_expire_minutes())

    password_reset_tokens_table.insert(
        {
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at.isoformat(),
            "used": False,
            "created_at": _now_utc().isoformat(),
        }
    )
    return token


def _get_user_doc_by_id(user_id: int) -> dict:
    doc = users_table.get(doc_id=user_id)
    if doc is None:
        raise HTTPException(status_code=400, detail="User account not found.")
    return doc


def _send_password_reset_email(*, to_email: str, reset_url: str) -> None:
    provider = os.getenv("PASSWORD_RESET_EMAIL_PROVIDER", "resend").lower()
    if provider != "resend":
        logger.error("Unsupported password-reset email provider configured.")
        raise HTTPException(status_code=500, detail=_GENERIC_EMAIL_FAILURE)

    resend_api_key = os.getenv("RESEND_API_KEY")
    email_from = os.getenv("EMAIL_FROM")
    if not resend_api_key or not email_from:
        logger.error("Email provider is not configured (missing env vars).")
        raise HTTPException(status_code=500, detail=_GENERIC_EMAIL_FAILURE)

    subject = "HealthCore: Restablecer contraseña"
    html = f"""
      <p>Recientemente solicitaste un restablecimiento de contraseña.</p>
      <p>Abre el siguiente enlace para crear una nueva contraseña:</p>
      <p><a href="{reset_url}">{reset_url}</a></p>
      <p>Este enlace expira en poco tiempo.</p>
    """

    payload = {
        "from": email_from,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "healthcore-api",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_context()) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        # Do not log recipient email (PII) or provider response body.
        logger.error(
            "Resend HTTP error when sending password reset (status=%s).",
            exc.code,
        )
        raise HTTPException(
            status_code=500,
            detail=_GENERIC_EMAIL_FAILURE,
        ) from exc
    except urllib.error.URLError:
        logger.error(
            "Resend network error when sending password reset (type=%s).",
            "URLError",
        )
        raise HTTPException(
            status_code=500,
            detail=_GENERIC_EMAIL_FAILURE,
        ) from None


def forgot_password(email: str) -> dict:
    """
    Accepts an email and, if the user exists, generates a token + sends an email.
    Always returns 200 to avoid user enumeration.
    """
    user_query = Query()
    rows = users_table.search(user_query.email == str(email))
    if not rows:
        return {"message": "ok"}

    user_doc = rows[0]
    user_id = int(user_doc.doc_id)
    to_email = str(user_doc["email"])

    frontend_base_url = os.getenv("FRONTEND_BASE_URL")
    if not frontend_base_url:
        logger.error("FRONTEND_BASE_URL is not configured; skipping token creation.")
        return {"message": "ok"}

    resend_api_key = os.getenv("RESEND_API_KEY")
    email_from = os.getenv("EMAIL_FROM")
    if not resend_api_key or not email_from:
        logger.error(
            "Email provider env incomplete; skipping token creation for user_id=%s.",
            user_id,
        )
        return {"message": "ok"}

    try:
        token = create_password_reset_token(user_id)
    except HTTPException:
        logger.warning(
            "Password reset token not created for user_id=%s (config error).",
            user_id,
        )
        return {"message": "ok"}

    reset_url = f"{frontend_base_url.rstrip('/')}/reset-password?token={token}"
    try:
        _send_password_reset_email(to_email=to_email, reset_url=reset_url)
    except HTTPException:
        logger.warning(
            "Password reset email not sent for user_id=%s.",
            user_id,
        )
        return {"message": "ok"}
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        logger.exception(
            "Expected transport/config error sending password reset for user_id=%s.",
            user_id,
        )
        return {"message": "ok"}

    return {"message": "ok"}


def reset_password(*, token: str, new_password: str) -> dict:
    token_hash = _sha256(token)
    query = Query()
    docs = password_reset_tokens_table.search(query.token_hash == token_hash)
    if not docs:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")

    record = docs[0]
    try:
        expires_at = datetime.fromisoformat(record["expires_at"])
    except (KeyError, TypeError, ValueError):
        logger.warning("Corrupt password-reset token expiry; treating as invalid.")
        raise HTTPException(status_code=400, detail="Invalid or expired token.") from None

    used = bool(record.get("used", False))

    if used or _now_utc() > expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")

    user_id = int(record["user_id"])

    _get_user_doc_by_id(user_id)
    password_hash = hash_password(new_password)
    users_table.update(
        {"hashed_password": password_hash},
        doc_ids=[user_id],
    )

    # Invalidate token: delete after successful use.
    password_reset_tokens_table.remove(query.token_hash == token_hash)

    return {"message": "ok"}


def change_password(*, user_id: int, current_password: str, new_password: str) -> dict:
    user_doc = _get_user_doc_by_id(user_id)
    hashed_password = user_doc["hashed_password"]

    if not verify_password(current_password, hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    password_hash = hash_password(new_password)
    users_table.update(
        {"hashed_password": password_hash},
        doc_ids=[user_id],
    )
    return {"message": "ok"}
