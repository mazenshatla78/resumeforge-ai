import hashlib
import hmac
import json
import os
from backend.config import (PADDLE_API_KEY, PADDLE_ENVIRONMENT, PADDLE_PRICE_MONTHLY, PADDLE_PRICE_ANNUAL,
                           PADDLE_CLIENT_TOKEN, PADDLE_WEBHOOK_SECRET)
import httpx


def _base_url():
    if PADDLE_ENVIRONMENT == "production":
        return "https://api.paddle.com"
    return "https://sandbox-api.paddle.com"


def is_configured():
    return all([PADDLE_API_KEY, PADDLE_CLIENT_TOKEN, PADDLE_WEBHOOK_SECRET, PADDLE_PRICE_MONTHLY, PADDLE_PRICE_ANNUAL])


def create_checkout(user, plan: str, db) -> dict:
    if not is_configured():
        raise RuntimeError("Paddle not configured")
    from backend.models import Payment
    price_id = PADDLE_PRICE_MONTHLY if plan == "monthly" else PADDLE_PRICE_ANNUAL
    amount = 19.0 if plan == "monthly" else 149.0
    # create pending payment row
    payment = Payment(user_id=user.id, provider="paddle", plan=plan, amount=amount, currency="USD", status="pending")
    db.add(payment)
    db.commit()
    db.refresh(payment)

    payload = {
        "items": [{"price_id": price_id, "quantity": 1}],
        "custom_data": {"user_id": str(user.id), "payment_id": str(payment.id), "plan": plan},
        "customer": {"email": user.email},
        "checkout": {"url": None},
    }
    try:
        resp = httpx.post(f"{_base_url()}/transactions", json=payload, headers={
            "Authorization": f"Bearer {PADDLE_API_KEY}",
            "Content-Type": "application/json",
        }, timeout=30)
        if resp.status_code not in (200, 201):
            payment.status = "failed"
            payment.error_message = f"Paddle {resp.status_code}: {resp.text[:500]}"
            db.commit()
            raise RuntimeError("Paddle checkout failed")
        data = resp.json().get("data", {})
        checkout_url = (data.get("checkout") or {}).get("url")
        payment.external_payment_id = data.get("id")
        db.commit()
        return {"provider": "paddle", "checkout_url": checkout_url, "payment_id": payment.id}
    except Exception as e:
        payment.status = "failed"
        payment.error_message = str(e)[:500]
        db.commit()
        raise


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    if not PADDLE_WEBHOOK_SECRET or not signature_header:
        return False
    # Paddle-Signature: ts=...;h1=...
    parts = {}
    for seg in signature_header.split(";"):
        if "=" in seg:
            k, v = seg.split("=", 1)
            parts[k.strip()] = v.strip()
    ts = parts.get("ts")
    h1 = parts.get("h1")
    if not ts or not h1:
        return False
    signed_payload = f"{ts}:{raw_body.decode('utf-8')}"
    expected = hmac.new(PADDLE_WEBHOOK_SECRET.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, h1)


def parse_webhook_event(raw_body: bytes) -> dict:
    return json.loads(raw_body.decode("utf-8"))
