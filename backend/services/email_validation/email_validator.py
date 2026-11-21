"""Email validation and domain classification."""
from __future__ import annotations

import re
import socket
from dataclasses import dataclass
from typing import Optional

from backend.services.email_validation.consumer_providers import is_consumer_provider, normalize_domain
from backend.services.email_validation.disposable_domains import is_disposable

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


@dataclass
class ValidationResult:
    status: str  # valid_consumer | valid_custom_domain | disposable_domain | invalid_email | invalid_domain | domain_unreachable | verification_required
    email: str
    domain: str
    is_disposable: bool
    is_consumer: bool
    is_business_candidate: bool
    mx_ok: bool | None
    message: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_syntax(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def classify_domain(domain: str) -> str:
    domain = normalize_domain(domain)
    if is_disposable(domain):
        return "disposable"
    if is_consumer_provider(domain):
        return "consumer"
    return "custom"


def mx_check(domain: str, timeout: float = 1.5) -> bool:
    """Best-effort MX record check. Returns True if MX records exist."""
    try:
        import dns.resolver
    except ImportError:
        # fallback: try socket resolution
        try:
            socket.gethostbyname(domain)
            return True
        except Exception:
            return False
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=timeout)
        return len(answers) > 0
    except Exception:
        # Try A record as fallback
        try:
            dns.resolver.resolve(domain, "A", lifetime=timeout)
            return True
        except Exception:
            return False


def validate_email(email: str, check_mx: bool = True) -> ValidationResult:
    email = normalize_email(email)
    if not validate_syntax(email):
        return ValidationResult("invalid_email", email, "", False, False, False, None, "Please enter a valid email address.")

    domain = email.split("@", 1)[1]
    domain = normalize_domain(domain)

    if is_disposable(domain):
        return ValidationResult("disposable_domain", email, domain, True, False, False, None,
                                "This email provider is not allowed. Please use a permanent email address.")

    consumer = is_consumer_provider(domain)

    mx_ok = None
    if check_mx:
        mx_ok = mx_check(domain)
        if not mx_ok:
            return ValidationResult("domain_unreachable", email, domain, False, consumer, not consumer, False,
                                    "This email domain does not appear to accept email. Please check the address.")

    if consumer:
        return ValidationResult("valid_consumer", email, domain, False, True, False, mx_ok,
                                "Email looks good.")

    # custom domain -> business candidate
    return ValidationResult("valid_custom_domain", email, domain, False, False, True, mx_ok,
                            "Business email detected. Eligible for Business plan.")
