import hashlib
import hmac
import json
import os
from backend.config import (PAYMOB_API_KEY, PAYMOB_SECRET_KEY, PAYMOB_PUBLIC_KEY,
                           PAYMOB_INTEGRATION_ID, PAYMOB_IFRAME_ID, PAYMOB_WEBHOOK_SECRET)
import httpx


BASE = "https://accept.paymob.com"


def is_configured():
    return all([PAYMOB_API_KEY, PAYMOB_SECRET_KEY, PAYMOB_PUBLIC_KEY,
                PAYMOB_INTEGRATION_ID, PAYMOB_IFRAME_ID])


def _auth_token():
    resp = httpx.post(f"{BASE}/api/auth/tokens", json={"api_key": PAYMOB_API_KEY}, timeout=30)
    resp.raise_for_status()
    return resp.json()["token"]


def create_checkout(user, plan: str, db) -> dict:
    if not is_configured():
        raise RuntimeError("Paymob not configured")
    from backend.models import Payment
    amount = 19.0 if plan == "monthly" else 149.0
    # Paymob amounts are in smallest currency unit (cents) for EGP? Use USD? Assume EGP not; use cents.
    amount_cents = int(amount * 100)
    payment = Payment(user_id=user.id, provider="paymob", plan=plan, amount=amount, currency="USD", status="pending")
    db.add(payment)
    db.commit()
    db.refresh(payment)

    try:
        token = _auth_token()
        # register order
        order_resp = httpx.post(f"{BASE}/api/ecommerce/orders", json={
            "auth_token": token,
            "delivery_needed": "false",
            "amount_cents": amount_cents,
            "currency": "USD",
            "items": [],
            "merchant_order_id": str(payment.id),
        }, timeout=30)
        order_resp.raise_for_status()
        order_id = order_resp.json()["id"]
        # payment key
        billing = {
            "apartment": "NA", "email": user.email, "floor": "NA", "first_name": (user.name or "Customer").split(" ")[0],
            "street": "NA", "building": "NA", "phone_number": "+201000000000", "shipping_method": "NA",
            "postal_code": "NA", "city": "NA", "country": "EG", "last_name": "NA", "state": "NA",
        }
        key_resp = httpx.post(f"{BASE}/api/acceptance/payment_keys", json={
            "auth_token": token,
            "amount_cents": amount_cents,
            "expiration": 3600,
            "order_id": order_id,
            "billing_data": billing,
            "currency": "USD",
            "integration_id": int(PAYMOB_INTEGRATION_ID),
        }, timeout=30)
        key_resp.raise_for_status()
        payment_token = key_resp.json()["token"]
        payment.external_order_id = str(order_id)
        db.commit()
        iframe_url = f"{BASE}/api/acceptance/iframes/{PAYMOB_IFRAME_ID}?payment_token={payment_token}"
        return {"provider": "paymob", "checkout_url": iframe_url, "payment_id": payment.id}
    except Exception as e:
        payment.status = "failed"
        payment.error_message = str(e)[:500]
        db.commit()
        raise


def verify_webhook_hmac(params: dict) -> bool:
    # Paymob HMAC: concatenate specific fields in order, HMAC-SHA512 with secret
    if not PAYMOB_WEBHOOK_SECRET:
        return False
    hmac_received = params.get("hmac")
    if not hmac_received:
        return False
    fields = ["amount_cents", "created_at", "currency", "error_occured", "has_parent_transaction",
              "id", "integration_id", "is_3d_secure", "is_auth", "is_capture", "is_refunded",
              "is_standalone_payment", "is_voided", "order", "owner", "pending", "source_data.pan",
              "source_data.sub_type", "source_data.type", "success"]
    # Build concatenated string from nested data
    data = params.get("obj", params)
    concat = ""
    for f in fields:
        val = data
        for part in f.split("."):
            if isinstance(val, dict):
                val = val.get(part, "")
            else:
                val = ""
        concat += str(val)
    expected = hmac.new(PAYMOB_WEBHOOK_SECRET.encode(), concat.encode(), hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, hmac_received)
