from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def email_delivery_configured() -> bool:
    return all(os.environ.get(name) for name in ("SMTP_HOST", "SMTP_FROM"))


def send_email(recipient: str, subject: str, body: str) -> None:
    host = os.environ.get("SMTP_HOST")
    sender = os.environ.get("SMTP_FROM")
    if not host or not sender:
        raise RuntimeError("Email delivery is not configured.")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    use_ssl = os.environ.get("SMTP_USE_SSL", "").lower() == "true"

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=20) as server:
                if username:
                    server.login(username, password or "")
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls(context=ssl.create_default_context())
                if username:
                    server.login(username, password or "")
                server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("Could not deliver transactional email.")
        raise RuntimeError("Transactional email delivery failed.") from exc
