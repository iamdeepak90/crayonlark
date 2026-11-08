"""Outgoing email over any SMTP provider (Brevo, Resend, SES, Zoho…). Never raises to callers."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from crayonlark.core.config import get_settings

log = logging.getLogger("crayonlark.smtp")


def enabled() -> bool:
    return bool(get_settings().smtp_host)


def send(
    to: str, subject: str, text: str, html: str | None = None, reply_to: str | None = None
) -> bool:
    s = get_settings()
    if not enabled():
        log.info("[smtp disabled] to=%s subject=%s\n%s", to, subject, text)
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.smtp_from, to, subject
    msg["Message-ID"] = make_msgid(domain="crayonlark.com")
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as smtp:
            if s.smtp_starttls:
                smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        log.error("email to %s failed: %s", to, exc)
        return False
