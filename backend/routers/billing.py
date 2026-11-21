import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.deps import get_current_user, audit, client_ip
from backend.models import Payment, WebhookEvent, Subscription, User
from backend.payments import provider_available
from backend.config import (PREMIUM_MONTHLY_PRICE, PREMIUM_ANNUAL_PRICE)
from backend.rate_limit import limiter

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _unavailable_message(provider_name: str):
    return {
        "error": "provider_unavailable",
        "message_en": "This payment method is temporarily unavailable due to a configuration or technical issue on our side. We apologize for the inconvenience. Please try again later or choose another available payment method.",
        "message_ar": "بوابة الدفع دي غير متاحة حاليًا بسبب إعدادات أو مشكلة فنية من جانبنا. نعتذر عن الإزعاج، يُرجى المحاولة مرة أخرى لاحقًا أو استخدام طريقة دفع أخرى متاحة.",
        "provider": provider_name,
    }


@router.get("/providers")
def providers(db: Session = Depends(get_db)):
    return {
        "paddle": {"available": provider_available("paddle", db)},
        "paymob": {"available": provider_available("paymob", db)},
    }


@router.post("/checkout")
@limiter.limit("10/minute")
def checkout(request: Request, payload: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    provider = (payload.get("provider") or "").lower()
    plan = (payload.get("plan") or "").lower()
    if provider not in ("paddle", "paymob"):
        raise HTTPException(400, "Invalid provider")
    if plan not in ("monthly", "annual"):
        raise HTTPException(400, "Invalid plan")
    if not provider_available(provider, db):
        raise HTTPException(503, detail=_unavailable_message(provider))
    try:
        if provider == "paddle":
            from backend import paddle_service
            result = paddle_service.create_checkout(user, plan, db)
        else:
            from backend import paymob_service
            result = paymob_service.create_checkout(user, plan, db)
    except Exception as e:
        raise HTTPException(502, "Payment provider error")
    audit(db, user, "billing.checkout_initiated", "payment", result.get("payment_id"), metadata={"provider": provider, "plan": plan}, ip=client_ip(request))
    return result


@router.post("/webhook/paddle")
async def paddle_webhook(request: Request, db: Session = Depends(get_db)):
    from backend import paddle_service
    raw = await request.body()
    sig = request.headers.get("Paddle-Signature", "")
    if not paddle_service.verify_webhook_signature(raw, sig):
        raise HTTPException(400, "Invalid signature")
    event = paddle_service.parse_webhook_event(raw)
    event_id = event.get("event_id") or event.get("id")
    # idempotency
    if event_id:
        existing = db.query(WebhookEvent).filter(WebhookEvent.provider == "paddle", WebhookEvent.event_id == event_id).first()
        if existing and existing.processed:
            return {"received": True, "duplicate": True}
        if not existing:
            db.add(WebhookEvent(provider="paddle", event_id=event_id, event_type=event.get("event_type"), processed=False))
            db.commit()
    # process
    try:
        _process_paddle_event(event, db)
        if event_id:
            we = db.query(WebhookEvent).filter(WebhookEvent.provider == "paddle", WebhookEvent.event_id == event_id).first()
            if we:
                we.processed = True
                we.processed_at = datetime_now()
                db.commit()
    except Exception as e:
        if event_id:
            we = db.query(WebhookEvent).filter(WebhookEvent.provider == "paddle", WebhookEvent.event_id == event_id).first()
            if we:
                we.error = str(e)[:500]
                db.commit()
        raise HTTPException(500, "Webhook processing failed")
    return {"received": True}


@router.post("/webhook/paymob")
async def paymob_webhook(request: Request, db: Session = Depends(get_db)):
    from backend import paymob_service
    # Paymob sends data as query params + body
    params = dict(request.query_params)
    try:
        body = await request.json()
    except Exception:
        body = {}
    params.update(body or {})
    if not paymob_service.verify_webhook_hmac(params):
        raise HTTPException(400, "Invalid HMAC")
    # idempotency by transaction id
    obj = params.get("obj", params)
    txn_id = str(obj.get("id") or params.get("id") or "")
    event_id = f"paymob:{txn_id}"
    existing = db.query(WebhookEvent).filter(WebhookEvent.provider == "paymob", WebhookEvent.event_id == event_id).first()
    if existing and existing.processed:
        return {"received": True, "duplicate": True}
    if not existing and txn_id:
        db.add(WebhookEvent(provider="paymob", event_id=event_id, event_type="transaction", processed=False))
        db.commit()
    try:
        _process_paymob_event(params, db)
        if txn_id:
            we = db.query(WebhookEvent).filter(WebhookEvent.provider == "paymob", WebhookEvent.event_id == event_id).first()
            if we:
                we.processed = True
                we.processed_at = datetime_now()
                db.commit()
    except Exception as e:
        if txn_id:
            we = db.query(WebhookEvent).filter(WebhookEvent.provider == "paymob", WebhookEvent.event_id == event_id).first()
            if we:
                we.error = str(e)[:500]
                db.commit()
        raise HTTPException(500, "Webhook processing failed")
    return {"received": True}


def datetime_now():
    from datetime import datetime
    return datetime.utcnow()


def _process_paddle_event(event: dict, db: Session):
    et = event.get("event_type", "")
    data = event.get("data", {})
    if et == "transaction.completed":
        custom = data.get("custom_data") or {}
        user_id = custom.get("user_id")
        payment_id = custom.get("payment_id")
        plan = custom.get("plan", "monthly")
        if not user_id:
            return
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            return
        # update payment
        if payment_id:
            p = db.query(Payment).filter(Payment.id == int(payment_id)).first()
            if p:
                p.status = "succeeded"
                p.external_payment_id = data.get("id")
                db.commit()
        # subscription
        period_end = None
        items = data.get("items", [])
        # Paddle provides billing period in data; fallback 30/365 days
        from datetime import timedelta
        now = datetime_now()
        if plan == "annual":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)
        sub = Subscription(user_id=user.id, provider="paddle", plan=plan, status="active",
                           external_subscription_id=data.get("subscription_id"),
                           external_customer_id=data.get("customer_id"),
                           current_period_start=now, current_period_end=period_end)
        db.add(sub)
        user.plan = "premium"
        db.commit()
    elif et in ("subscription.canceled", "subscription.cancelled"):
        sub_id = data.get("id")
        if sub_id:
            sub = db.query(Subscription).filter(Subscription.external_subscription_id == sub_id).first()
            if sub:
                sub.status = "cancelled"
                sub.cancel_at_period_end = True
                db.commit()
    elif et == "subscription.updated":
        pass


def _process_paymob_event(params: dict, db: Session):
    obj = params.get("obj", params)
    success = str(obj.get("success", "")).lower() == "true"
    pending = obj.get("pending", False)
    txn_id = str(obj.get("id", ""))
    merchant_order_id = obj.get("order", {}).get("merchant_order_id") if isinstance(obj.get("order"), dict) else None
    # find payment by id (merchant_order_id stores our payment id)
    payment = None
    if merchant_order_id:
        try:
            payment = db.query(Payment).filter(Payment.id == int(merchant_order_id)).first()
        except Exception:
            payment = None
    if payment:
        if success and not pending:
            payment.status = "succeeded"
            payment.external_payment_id = txn_id
        elif pending:
            payment.status = "pending"
        else:
            payment.status = "failed"
            payment.error_message = str(obj.get("data", {}).get("message", ""))[:500]
        db.commit()
        if success and not pending:
            user = db.query(User).filter(User.id == payment.user_id).first()
            if user:
                user.plan = "premium"
                from datetime import timedelta
                now = datetime_now()
                period_end = now + (timedelta(days=365) if payment.plan == "annual" else timedelta(days=30))
                sub = Subscription(user_id=user.id, provider="paymob", plan=payment.plan, status="active",
                                   external_subscription_id=txn_id, current_period_start=now, current_period_end=period_end)
                db.add(sub)
                db.commit()


# Backward compat endpoints
@router.get("/country")
def detect_country(request: Request):
    """Detect user's country from request headers (Vercel, Cloudflare, etc.)."""
    country = None
    # Vercel
    country = request.headers.get("x-vercel-ip-country")
    # Cloudflare
    if not country:
        country = request.headers.get("cf-ipcountry")
    # AWS ALB
    if not country:
        country = request.headers.get("x-amzn-trace-id", "").split("Country=")[-1].split(";")[0] if "Country=" in request.headers.get("x-amzn-trace-id", "") else None
    # Generic
    if not country:
        country = request.headers.get("x-country-code")
    if country and country.upper() in ("XX", "T1", "UNKNOWN", ""):
        country = None
    return {"country": country.upper() if country else None}


@router.get("/paddle-config")
def paddle_config():
    """Return Paddle client-side config (environment + client token). No API key."""
    from backend.config import PADDLE_CLIENT_TOKEN, PADDLE_ENVIRONMENT
    env = PADDLE_ENVIRONMENT or ""
    token = PADDLE_CLIENT_TOKEN or ""
    if not env or not token:
        raise HTTPException(503, "Paddle not configured")
    if env not in ("sandbox", "production", "live"):
        raise HTTPException(503, "Invalid Paddle environment")
    return {"environment": env, "clientToken": token}


@router.get("/paddle-prices")
def paddle_prices():
    """Return the tier price IDs for Paddle PricePreview."""
    tiers = [
        {"name": "Starter", "description": "Perfect for getting started", "features": ["3 scans per month", "AI resume analysis", "Basic recommendations", "PDF export"], "priceId": {"month": "pri_01m7wha5m5jx2eygtpny4padhs", "year": "pri_01m7wha7ja3t0eekyew2gxz01j"}},
        {"name": "Pro", "description": "For serious job seekers", "features": ["Unlimited scans", "AI resume analysis", "Advanced recommendations", "Cover letter generation", "Interview prep", "PDF & DOCX export"], "priceId": {"month": "pri_01m7wgbxsqq12dc5tpbqqmtctj", "year": "pri_01m7wgc14ts8czy5b0a2zm2njv"}},
        {"name": "Advanced", "description": "For career professionals", "features": ["Everything in Pro", "Priority support", "Custom templates", "Team sharing", "Analytics dashboard"], "priceId": {"month": "pri_01m7whabe236xs6qtx0nr88bnn", "year": "pri_01m7whad93xv90jk9cyx8d0qn8"}},
    ]
    return {"tiers": tiers}


@router.get("/status")
def status(user=Depends(get_current_user)):
    return {"plan": user.plan}

@router.post("/demo-upgrade")
def demo_upgrade(user=Depends(get_current_user), db: Session = Depends(get_db)):
    user.plan = "premium"
    db.commit()
    return {"ok": True, "plan": user.plan, "note": "Demo upgrade applied (no real payment)."}