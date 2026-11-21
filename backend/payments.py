import os
from abc import ABC, abstractmethod


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def is_enabled(self, db) -> bool:
        ...

    @abstractmethod
    def create_checkout(self, user, plan: str, db) -> dict:
        ...

    @abstractmethod
    def verify_webhook(self, request, db) -> dict:
        ...


def provider_available(provider: str, db) -> bool:
    """Check config + admin toggle."""
    from backend.config import (PADDLE_API_KEY, PADDLE_CLIENT_TOKEN, PADDLE_WEBHOOK_SECRET,
                               PADDLE_PRICE_MONTHLY, PADDLE_PRICE_ANNUAL,
                               PAYMOB_API_KEY, PAYMOB_SECRET_KEY, PAYMOB_PUBLIC_KEY,
                               PAYMOB_INTEGRATION_ID, PAYMOB_IFRAME_ID)
    from backend.models import SystemSetting
    if provider == "paddle":
        configured = all([PADDLE_API_KEY, PADDLE_CLIENT_TOKEN, PADDLE_WEBHOOK_SECRET,
                          PADDLE_PRICE_MONTHLY, PADDLE_PRICE_ANNUAL])
        toggle = db.query(SystemSetting).filter(SystemSetting.key == "paddle_enabled").first()
        enabled = (toggle.value == "true") if toggle else True
        return configured and enabled
    if provider == "paymob":
        configured = all([PAYMOB_API_KEY, PAYMOB_SECRET_KEY, PAYMOB_PUBLIC_KEY,
                          PAYMOB_INTEGRATION_ID, PAYMOB_IFRAME_ID])
        toggle = db.query(SystemSetting).filter(SystemSetting.key == "paymob_enabled").first()
        enabled = (toggle.value == "true") if toggle else True
        return configured and enabled
    return False
