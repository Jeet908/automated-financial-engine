from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Subscription, User, WebhookEvent, get_db, utc_now
from .dependencies import get_verified_user
from .plans import account_summary, effective_plan, plan_catalog
from .security import check_csrf

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    stripe = None  # type: ignore
    STRIPE_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/billing", tags=["billing"])
RAZORPAY_API = "https://api.razorpay.com/v1"


class CheckoutRequest(BaseModel):
    plan_key: str


class StripeCheckoutRequest(BaseModel):
    plan_key: str
    currency: str = "usd"
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutVerification(BaseModel):
    razorpay_subscription_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def _public_base_url(request: Request) -> str:
    configured = os.environ.get("PUBLIC_APP_URL")
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if configured:
        return configured.rstrip("/")
    if railway_domain:
        return f"https://{railway_domain}".rstrip("/")
    return str(request.base_url).rstrip("/")


def _stripe_price_id(plan_key: str, currency: str = "usd") -> str:
    cur = currency.upper()
    pk = plan_key.upper()
    return (
        os.environ.get(f"STRIPE_PRICE_ID_{pk}_{cur}")
        or os.environ.get(f"STRIPE_PRICE_ID_{pk}")
        or f"price_test_{plan_key}_{currency.lower()}"
    )


def _credentials() -> tuple[str, str]:
    key_id = os.environ.get("RAZORPAY_KEY_ID")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Razorpay checkout is not configured yet.")
    return key_id, key_secret


def _subscription_expiry(entity: dict[str, Any]) -> datetime | None:
    value = entity.get("current_end") or entity.get("end_at")
    if not value:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


async def _razorpay_request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    key_id, key_secret = _credentials()
    try:
        async with httpx.AsyncClient(timeout=20, auth=(key_id, key_secret)) as client:
            response = await client.request(
                method,
                f"{RAZORPAY_API}{path}",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Razorpay API returned HTTP %s for %s.", exc.response.status_code, path)
        raise HTTPException(status_code=502, detail="The payment provider could not process this request.")
    except httpx.HTTPError:
        logger.exception("Could not reach Razorpay.")
        raise HTTPException(status_code=502, detail="The payment provider is temporarily unavailable.")


@router.get("/plans")
def public_plans() -> dict[str, object]:
    catalog = plan_catalog()
    plans: list[dict[str, object]] = []
    for key, plan in catalog.items():
        env_name = plan["razorpay_plan_env"]
        plans.append(
            {
                "key": key,
                "name": plan["name"],
                "price_paise": plan["price_paise"],
                "currency": "INR",
                "prices": plan.get("prices", {"USD": 0, "INR": 0, "EUR": 0, "GBP": 0}),
                "trial_days": plan.get("trial_days", 0),
                "features": plan.get("features", []),
                "monthly_valuations": plan["monthly_valuations"],
                "checkout_available": (
                    (
                        bool(
                            os.environ.get("RAZORPAY_KEY_ID")
                            and os.environ.get("RAZORPAY_KEY_SECRET")
                            and os.environ.get("RAZORPAY_WEBHOOK_SECRET")
                        )
                        and bool(env_name and os.environ.get(str(env_name)))
                    )
                    or bool(os.environ.get("STRIPE_SECRET_KEY") or STRIPE_AVAILABLE)
                )
                if key not in ("free", "free_trial")
                else True,
            }
        )
    return {"plans": plans}


@router.post("/checkout")
async def create_checkout(
    payload: CheckoutRequest,
    request: Request,
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    check_csrf(request)
    if payload.plan_key not in {"pro", "business"}:
        raise HTTPException(status_code=422, detail="Choose a paid plan to start checkout.")

    current_subscription = db.get(Subscription, user.id)
    current_plan, _ = effective_plan(db, user.id)
    if current_plan != "free":
        raise HTTPException(status_code=409, detail="Cancel or change your existing subscription before checking out.")

    catalog = plan_catalog()
    plan = catalog[payload.plan_key]
    plan_env = str(plan["razorpay_plan_env"])
    provider_plan_id = os.environ.get(plan_env)
    if not provider_plan_id:
        raise HTTPException(status_code=503, detail=f"The {plan['name']} subscription plan is not configured.")

    if current_subscription and current_subscription.provider_subscription_id:
        if current_subscription.status in {"created", "pending", "authenticated"}:
            if (
                current_subscription.plan_key != payload.plan_key
                or current_subscription.provider_plan_id != provider_plan_id
            ):
                raise HTTPException(status_code=409, detail="Finish or cancel your existing checkout first.")
            key_id, _ = _credentials()
            return {
                "key_id": key_id,
                "subscription_id": current_subscription.provider_subscription_id,
                "name": "MarketLens Analytics",
                "description": f"{plan['name']} monthly subscription",
                "plan_key": payload.plan_key,
                "amount_paise": plan["price_paise"],
                "email": user.email,
            }

    provider_plan = await _razorpay_request("GET", f"/plans/{provider_plan_id}")
    item = provider_plan.get("item") or {}
    if (
        item.get("amount") != plan["price_paise"]
        or item.get("currency") != "INR"
        or provider_plan.get("period") != "monthly"
        or provider_plan.get("interval") != 1
    ):
        logger.error("Configured Razorpay plan %s does not match the application catalog.", payload.plan_key)
        raise HTTPException(
            status_code=503,
            detail=f"The configured {plan['name']} Razorpay plan must be monthly and match the displayed INR price.",
        )

    provider_subscription = await _razorpay_request(
        "POST",
        "/subscriptions",
        payload={
            "plan_id": provider_plan_id,
            "total_count": 120,
            "quantity": 1,
            "customer_notify": 1,
            "notes": {"user_id": user.id, "plan_key": payload.plan_key},
        },
    )
    provider_id = provider_subscription.get("id")
    if not provider_id:
        logger.error("Razorpay subscription creation returned no subscription identifier.")
        raise HTTPException(status_code=502, detail="The payment provider returned an incomplete checkout response.")

    subscription = current_subscription or Subscription(user_id=user.id, tenant_id=user.tenant_id)
    subscription.provider = "razorpay"
    subscription.provider_subscription_id = str(provider_id)
    subscription.provider_plan_id = provider_plan_id
    subscription.plan_key = payload.plan_key
    subscription.status = str(provider_subscription.get("status", "created"))
    subscription.current_period_end = _subscription_expiry(provider_subscription)
    subscription.cancel_at_period_end = False
    db.add(subscription)
    db.commit()
    return {
        "key_id": os.environ["RAZORPAY_KEY_ID"],
        "subscription_id": provider_id,
        "name": "MarketLens Analytics",
        "description": f"{plan['name']} monthly subscription",
        "plan_key": payload.plan_key,
        "amount_paise": plan["price_paise"],
        "email": user.email,
    }


@router.post("/verify")
async def verify_checkout(
    payload: CheckoutVerification,
    request: Request,
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    check_csrf(request)
    _, key_secret = _credentials()
    subscription = db.get(Subscription, user.id)
    if not subscription or subscription.provider_subscription_id != payload.razorpay_subscription_id:
        raise HTTPException(status_code=400, detail="This payment does not match your account.")
    expected_signature = hmac.new(
        key_secret.encode("utf-8"),
        f"{payload.razorpay_payment_id}|{payload.razorpay_subscription_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, payload.razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment verification failed.")

    provider_subscription = await _razorpay_request(
        "GET",
        f"/subscriptions/{payload.razorpay_subscription_id}",
    )
    notes = provider_subscription.get("notes") or {}
    if notes.get("user_id") != user.id or notes.get("plan_key") != subscription.plan_key:
        raise HTTPException(status_code=400, detail="This payment does not match your account or selected plan.")
    subscription.status = str(provider_subscription.get("status", "pending"))
    subscription.current_period_end = _subscription_expiry(provider_subscription)
    subscription.updated_at = utc_now()
    db.commit()
    return {
        "status": subscription.status,
        "account": account_summary(db, user),
        "message": (
            "Subscription activated."
            if subscription.status in {"active", "trialing"}
            else "Payment received. Subscription activation is being confirmed."
        ),
    }


@router.post("/cancel")
async def cancel_subscription(
    request: Request,
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    check_csrf(request)
    subscription = db.get(Subscription, user.id)
    if (
        subscription is None
        or subscription.provider != "razorpay"
        or not subscription.provider_subscription_id
        or subscription.status not in {"active", "trialing", "authenticated"}
    ):
        raise HTTPException(status_code=409, detail="There is no active subscription to cancel.")
    await _razorpay_request(
        "POST",
        f"/subscriptions/{subscription.provider_subscription_id}/cancel",
        payload={"cancel_at_cycle_end": 1},
    )
    subscription.cancel_at_period_end = True
    subscription.updated_at = utc_now()
    db.commit()
    return {"status": "cancellation_scheduled", "message": "Your subscription will remain active until the billing period ends."}


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
    event_id: str | None = Header(default=None, alias="X-Razorpay-Event-Id"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET")
    if not webhook_secret or not signature:
        raise HTTPException(status_code=503, detail="Razorpay webhooks are not configured.")
    body = await request.body()
    expected = hmac.new(webhook_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Webhook signature verification failed.")
    payload = await request.json()
    event_name = str(payload.get("event", ""))
    event_id = event_id or hashlib.sha256(body).hexdigest()
    if db.get(WebhookEvent, event_id):
        return {"status": "already_processed"}

    entity = (
        (payload.get("payload") or {})
        .get("subscription", {})
        .get("entity", {})
    )
    provider_id = entity.get("id")
    subscription = db.scalar(
        select(Subscription).where(Subscription.provider_subscription_id == provider_id)
    ) if provider_id else None
    db.add(WebhookEvent(event_id=event_id))
    if subscription:
        status_by_event = {
            "subscription.activated": "active",
            "subscription.charged": "active",
            "subscription.resumed": "active",
            "subscription.paused": "paused",
            "subscription.halted": "halted",
            "subscription.cancelled": "cancelled",
            "subscription.completed": "completed",
        }
        if event_name in status_by_event:
            subscription.status = status_by_event[event_name]
        elif entity.get("status"):
            subscription.status = str(entity["status"])
        subscription.current_period_end = _subscription_expiry(entity)
        subscription.updated_at = utc_now()
    db.commit()
    return {"status": "accepted"}


@router.post("/stripe/checkout")
async def create_stripe_checkout(
    payload: StripeCheckoutRequest,
    request: Request,
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    check_csrf(request)
    if payload.plan_key not in {"pro", "business"}:
        raise HTTPException(status_code=422, detail="Choose a paid plan (pro or business) to start checkout.")

    currency = payload.currency.lower()
    if currency not in {"usd", "eur", "gbp", "inr"}:
        raise HTTPException(status_code=422, detail="Supported currencies are USD, EUR, GBP, and INR.")

    current_plan, _ = effective_plan(db, user.id)
    if current_plan not in {"free", "free_trial"}:
        raise HTTPException(status_code=409, detail="Cancel or change your existing subscription before checking out.")

    base_url = _public_base_url(request)
    success_url = payload.success_url or f"{base_url}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = payload.cancel_url or f"{base_url}/?checkout=cancel"

    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    price_id = _stripe_price_id(payload.plan_key, currency)

    if stripe_key and stripe is not None:
        try:
            stripe.api_key = stripe_key
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                customer_email=user.email,
                client_reference_id=user.id,
                subscription_data={
                    "trial_period_days": 14,
                    "metadata": {
                        "user_id": user.id,
                        "tenant_id": getattr(user, "tenant_id", user.id),
                        "plan_key": payload.plan_key,
                    },
                },
                metadata={
                    "user_id": user.id,
                    "tenant_id": getattr(user, "tenant_id", user.id),
                    "plan_key": payload.plan_key,
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "provider": "stripe",
                "plan_key": payload.plan_key,
            }
        except Exception as exc:
            logger.warning("Stripe checkout session creation encountered: %s", exc)
            mock_id = f"cs_test_{uuid4().hex[:16]}"
            mock_url = f"{base_url}/?mock_stripe_checkout=1&session_id={mock_id}&plan={payload.plan_key}&currency={currency}"
            return {
                "checkout_url": mock_url,
                "session_id": mock_id,
                "provider": "stripe",
                "plan_key": payload.plan_key,
                "mode": "test_fallback",
            }

    # Zero-credential mock session for local tests and offline dev
    mock_id = f"cs_test_{uuid4().hex[:16]}"
    mock_url = f"{base_url}/?mock_stripe_checkout=1&session_id={mock_id}&plan={payload.plan_key}&currency={currency}"
    return {
        "checkout_url": mock_url,
        "session_id": mock_id,
        "provider": "stripe",
        "plan_key": payload.plan_key,
        "mode": "mock",
    }


@router.post("/stripe/portal")
async def create_stripe_portal(
    request: Request,
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    check_csrf(request)
    base_url = _public_base_url(request)
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    sub = db.get(Subscription, user.id)

    if stripe_key and stripe is not None and sub and sub.provider_subscription_id:
        try:
            stripe.api_key = stripe_key
            stripe_sub = stripe.Subscription.retrieve(sub.provider_subscription_id)
            customer_id = getattr(stripe_sub, "customer", None)
            if customer_id:
                portal_session = stripe.billing_portal.Session.create(
                    customer=str(customer_id),
                    return_url=base_url,
                )
                return {"portal_url": portal_session.url}
        except Exception as exc:
            logger.warning("Stripe billing portal session creation: %s", exc)

    mock_url = f"{base_url}/?portal=stripe_billing_mock"
    return {"portal_url": mock_url}


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    body = await request.body()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    event: dict[str, Any] = {}
    if webhook_secret and stripe is not None:
        if not signature:
            raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")
        try:
            event = stripe.Webhook.construct_event(body, signature, webhook_secret)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {exc}")
    else:
        try:
            event = json.loads(body.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON webhook payload.")

    event_id = event.get("id") or hashlib.sha256(body).hexdigest()
    if db.get(WebhookEvent, event_id):
        return {"status": "already_processed"}

    db.add(WebhookEvent(event_id=event_id))
    event_type = str(event.get("type", ""))
    data_obj = (event.get("data") or {}).get("object", {})

    if event_type == "checkout.session.completed":
        user_id = data_obj.get("client_reference_id") or (data_obj.get("metadata") or {}).get("user_id")
        plan_key = (data_obj.get("metadata") or {}).get("plan_key", "pro")
        sub_id = data_obj.get("subscription")
        if user_id:
            sub = db.get(Subscription, user_id)
            if not sub:
                user = db.get(User, user_id)
                tenant_id = getattr(user, "tenant_id", None) or getattr(user, "org_id", None) or user_id
                sub = Subscription(user_id=user_id, tenant_id=tenant_id)
                db.add(sub)
            sub.provider = "stripe"
            sub.provider_subscription_id = str(sub_id) if sub_id else f"sub_{uuid4().hex[:12]}"
            sub.plan_key = plan_key
            sub.status = "active"
            sub.current_period_end = utc_now() + timedelta(days=30)
            sub.cancel_at_period_end = False
            sub.updated_at = utc_now()

    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        sub_id = data_obj.get("id")
        if sub_id:
            sub = db.scalar(select(Subscription).where(Subscription.provider_subscription_id == str(sub_id)))
            if sub:
                status = data_obj.get("status", sub.status)
                sub.status = "active" if status in ("active", "trialing") else status
                if data_obj.get("cancel_at_period_end") is not None:
                    sub.cancel_at_period_end = bool(data_obj.get("cancel_at_period_end"))
                if data_obj.get("current_period_end"):
                    sub.current_period_end = datetime.fromtimestamp(int(data_obj["current_period_end"]), tz=timezone.utc)
                sub.updated_at = utc_now()

    elif event_type == "customer.subscription.deleted":
        sub_id = data_obj.get("id")
        if sub_id:
            sub = db.scalar(select(Subscription).where(Subscription.provider_subscription_id == str(sub_id)))
            if sub:
                sub.status = "cancelled"
                sub.updated_at = utc_now()

    elif event_type == "invoice.payment_succeeded":
        sub_id = data_obj.get("subscription")
        if sub_id:
            sub = db.scalar(select(Subscription).where(Subscription.provider_subscription_id == str(sub_id)))
            if sub:
                sub.status = "active"
                sub.updated_at = utc_now()

    elif event_type == "invoice.payment_failed":
        sub_id = data_obj.get("subscription")
        if sub_id:
            sub = db.scalar(select(Subscription).where(Subscription.provider_subscription_id == str(sub_id)))
            if sub:
                sub.status = "past_due"
                sub.updated_at = utc_now()

    db.commit()
    return {"status": "accepted"}
