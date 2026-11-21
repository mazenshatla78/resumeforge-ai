import hashlib
import hmac
import json


def test_paddle_webhook_invalid_signature(client):
    r = client.post("/api/billing/webhook/paddle", content=b"{}", headers={"Paddle-Signature": "ts=1;h1=bad"})
    assert r.status_code == 400


def test_paymob_webhook_invalid_hmac(client):
    r = client.post("/api/billing/webhook/paymob", json={"success": "true"})
    assert r.status_code == 400


def test_providers_endpoint(client):
    r = client.get("/api/billing/providers")
    assert r.status_code == 200
    assert "paddle" in r.json() and "paymob" in r.json()


def test_checkout_paddle_configured(client, auth_headers):
    headers, info = auth_headers
    r = client.post("/api/billing/checkout", json={"provider": "paddle", "plan": "monthly"}, headers=headers)
    # Paddle is configured (live keys present) -> 200 or 502 (provider error in sandbox)
    assert r.status_code in (200, 502)
    if r.status_code == 200:
        assert "checkout_url" in r.json()
