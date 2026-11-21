"""Email sending service. Uses SMTP when configured; otherwise logs (dev mode)."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from backend.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, APP_BASE_URL


def is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_PORT)


def send_email(to: str, subject: str, body: str, html: str | None = None) -> bool:
    if not is_configured():
        return False
    try:
        msg = EmailMessage()
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        if html:
            msg.add_alternative(html, subtype="html")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[email] failed to send to {to}: {e}")
        return False


def send_verification_email(to: str, link: str) -> bool:
    subject = "Verify your ResumeForge AI email"
    body = f"Welcome to ResumeForge AI!\n\nPlease verify your email by clicking this link:\n{link}\n\nThis link expires in 24 hours.\n\nIf you didn't create an account, ignore this email."
    html = f"<p>Welcome to ResumeForge AI!</p><p>Please verify your email by clicking <a href='{link}'>this link</a>.</p><p>This link expires in 24 hours.</p>"
    return send_email(to, subject, body, html)


def send_password_reset_email(to: str, link: str) -> bool:
    subject = "Reset your ResumeForge AI password"
    body = f"You requested a password reset.\n\nClick here to reset: {link}\n\nThis link expires in 1 hour.\n\nIf you didn't request this, ignore this email."
    html = f"<p>You requested a password reset.</p><p>Click <a href='{link}'>here</a> to reset your password.</p><p>This link expires in 1 hour.</p>"
    return send_email(to, subject, body, html)
