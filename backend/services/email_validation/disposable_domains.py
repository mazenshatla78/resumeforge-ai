"""Disposable email domain blocklist loader and checker."""
from __future__ import annotations

import os
from pathlib import Path

_BASE = Path(__file__).resolve().parent
_BLOCKLIST_FILE = _BASE / "disposable_domains.txt"

# In-memory cache
_cache: set[str] | None = None


def _load() -> set[str]:
    global _cache
    if _cache is not None:
        return _cache
    domains: set[str] = set()
    if _BLOCKLIST_FILE.exists():
        with _BLOCKLIST_FILE.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip().lower()
                if line and not line.startswith("#"):
                    domains.add(line)
    _cache = domains
    return domains


def reload() -> int:
    global _cache
    _cache = None
    return len(_load())


def is_disposable(domain: str) -> bool:
    domain = domain.lower().strip().rstrip(".").lstrip("@")
    domains = _load()
    if domain in domains:
        return True
    # subdomain matching: if parent domain is disposable
    parts = domain.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[i:])
        if parent in domains:
            return True
    return False


def count() -> int:
    return len(_load())
