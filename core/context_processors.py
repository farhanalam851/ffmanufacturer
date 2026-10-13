from django.conf import settings

from .models import SiteSetting


def site(request):
    try:
        setting = SiteSetting.load()
    except Exception:  # database not migrated yet
        setting = None
    cart = request.session.get("cart", {}) if hasattr(request, "session") else {}
    return {
        "SITE": setting,
        "csp_nonce": getattr(request, "csp_nonce", ""),
        "GA_ID": settings.GA_MEASUREMENT_ID,
        "CART_COUNT": sum(int(i.get("q", 0)) for i in cart.values()),
    }
