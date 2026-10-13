"""Razorpay helpers. Only the REST API and HMAC verification are used, so no extra SDK is needed."""
import hashlib
import hmac

import requests
from django.conf import settings
from django.utils import timezone

API = "https://api.razorpay.com/v1"


def is_configured():
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def demo_mode():
    """Demo payments are only possible with DEBUG on and no live keys."""
    return settings.DEBUG and not is_configured()


def create_order(order):
    """Create (or reuse) the Razorpay order for this shop order. Returns the Razorpay order id."""
    if order.razorpay_order_id:
        return order.razorpay_order_id
    resp = requests.post(
        f"{API}/orders",
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        json={"amount": int(order.total * 100), "currency": "INR", "receipt": order.order_number,
              "notes": {"order_number": order.order_number}},
        timeout=15,
    )
    resp.raise_for_status()
    order.razorpay_order_id = resp.json()["id"]
    order.save(update_fields=["razorpay_order_id"])
    return order.razorpay_order_id


def verify_signature(razorpay_order_id, payment_id, signature):
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(), f"{razorpay_order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def verify_webhook(body, signature):
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return False
    expected = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def mark_paid(order, payment_id=""):
    """Idempotent: safe to call from both the browser callback and the webhook."""
    if order.payment_status == "paid":
        return False
    order.payment_status = "paid"
    order.razorpay_payment_id = payment_id or order.razorpay_payment_id
    order.paid_at = timezone.now()
    if order.status == "pending":
        order.status = "confirmed"
    order.save()
    return True
