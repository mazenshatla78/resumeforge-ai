"""Consumer email provider allowlist and helpers."""
from __future__ import annotations

# Major legitimate consumer email providers.
# Easy to update: add domains here.
CONSUMER_PROVIDERS = {
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "yahoo.com",
    "yahoo.co.uk",
    "yahoo.co.in",
    "icloud.com",
    "me.com",
    "mac.com",
    "protonmail.com",
    "proton.me",
    "pm.me",
    "aol.com",
    "zoho.com",
    "mail.com",
    "gmx.com",
    "gmx.net",
    "yandex.com",
    "yandex.ru",
    "tutanota.com",
    "tutamail.com",
    "fastmail.com",
    "hey.com",
    "duck.com",
}

# Free-tier / webmail providers that are not strictly consumer but acceptable
ADDITIONAL_WEBMAIL = {
    "mail.ru",
    "bk.ru",
    "list.ru",
    "inbox.ru",
    "rambler.ru",
}


def is_consumer_provider(domain: str) -> bool:
    domain = domain.lower().strip().lstrip("@")
    return domain in CONSUMER_PROVIDERS or domain in ADDITIONAL_WEBMAIL


def normalize_domain(domain: str) -> str:
    return domain.lower().strip().rstrip(".").lstrip("@")
