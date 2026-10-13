"""Security middleware and small helpers: response headers, CSP with nonces, and rate limiting."""
import hashlib
import secrets

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.urls import NoReverseMatch, reverse

PRIVATE_PREFIXES = ("/account/", "/manage/", "/cart", "/checkout", "/payment/", "/orders/", "/thank-you/")


def client_ip(request):
    """Best-effort client IP. Proxy headers are only trusted when TRUST_PROXY_HEADERS is on (set on Vercel)."""
    if settings.TRUST_PROXY_HEADERS:
        h = request.META
        for key in ("HTTP_X_VERCEL_FORWARDED_FOR", "HTTP_X_REAL_IP"):
            if h.get(key):
                return h[key].split(",")[0].strip()
        if h.get("HTTP_X_FORWARDED_FOR"):
            return h["HTTP_X_FORWARDED_FOR"].split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _key(request, scope, extra=""):
    raw = f"{scope}|{client_ip(request)}|{extra}".encode()
    return "rl:" + hashlib.sha256(raw).hexdigest()[:40]


def is_blocked(request, scope, limit, extra=""):
    try:
        return int(cache.get(_key(request, scope, extra), 0)) >= limit
    except Exception:  # never take the site down because the cache is unavailable
        return False


def register_hit(request, scope, window, extra=""):
    key = _key(request, scope, extra)
    try:
        cache.add(key, 0, window)
        cache.incr(key)
    except Exception:
        pass


def clear_hits(request, scope, extra=""):
    try:
        cache.delete(_key(request, scope, extra))
    except Exception:
        pass


def too_many(message="Too many attempts. Please wait a few minutes and try again."):
    return HttpResponse(message, status=429, content_type="text/plain", headers={"Retry-After": "900"})


def throttle_post(request, scope, limit, window):
    """Count every POST. Returns True when the caller is over the limit."""
    if is_blocked(request, scope, limit):
        return True
    register_hit(request, scope, window)
    return False


class SecurityMiddleware:
    """Adds CSP (per-request nonce), Permissions-Policy and no-store for private pages, and
    brute-force protection for the login forms (site and admin)."""

    LOGIN_LIMIT = 8
    LOGIN_WINDOW = 15 * 60

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_paths = set()
        for name in ("accounts:login", "admin:login"):
            try:
                self.login_paths.add(reverse(name))
            except NoReverseMatch:
                pass

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        is_login_post = request.method == "POST" and request.path in self.login_paths
        if is_login_post and is_blocked(request, "login", self.LOGIN_LIMIT):
            return too_many("Too many failed log-in attempts. Please wait 15 minutes and try again.")
        response = self.get_response(request)
        if is_login_post:
            if response.status_code == 200:  # form shown again = failed attempt
                register_hit(request, "login", self.LOGIN_WINDOW)
            elif response.status_code in (301, 302):
                clear_hits(request, "login")
        self.add_headers(request, response)
        return response

    def add_headers(self, request, response):
        nonce = request.csp_nonce
        csp = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}' https://checkout.razorpay.com https://www.googletagmanager.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com data:",
            "img-src 'self' data: blob: https:",
            "connect-src 'self' https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com https://api.razorpay.com https://lumberjack.razorpay.com",
            "frame-src https://api.razorpay.com https://checkout.razorpay.com",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "frame-ancestors 'none'",
        ]
        if not settings.DEBUG:
            csp.append("upgrade-insecure-requests")
        response.headers.setdefault("Content-Security-Policy", "; ".join(csp))
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), usb=(), interest-cohort=()")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if request.path.startswith(PRIVATE_PREFIXES + ("/" + settings.ADMIN_URL,)):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        if request.path.startswith(PRIVATE_PREFIXES):
            response.headers["Cache-Control"] = "private, no-store"
