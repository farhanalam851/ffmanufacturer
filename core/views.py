from django.contrib import messages
from django.core.mail import mail_admins
from django.shortcuts import redirect, render
from django.http import HttpResponse

from store.models import Category, Product

from .forms import EnquiryForm
from .security import throttle_post, too_many


def home(request):
    featured = Product.objects.active().with_rating().filter(is_featured=True)[:8]
    new_in = Product.objects.active().with_rating().order_by("-created")[:4]
    categories = Category.objects.filter(is_active=True)[:8]
    return render(request, "core/home.html", {"featured": featured, "new_in": new_in, "home_categories": categories})


def about(request):
    return render(request, "core/about.html")


def _enquiry(request, kind, template, initial=None):
    form = EnquiryForm(request.POST if request.method == "POST" else None, kind=kind, initial=initial)
    if request.method == "POST" and throttle_post(request, "enquiry", 6, 3600):
        return too_many("Too many messages from this connection. Please call us instead.")
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data.get("website"):  # honeypot filled in: a bot. Pretend it worked, store nothing.
            request.session["thanks_kind"] = kind
            return redirect("core:thank_you")
        enquiry = form.save()
        try:
            mail_admins(f"New {enquiry.get_kind_display()}: {enquiry.name}", enquiry.message, fail_silently=True)
        except Exception:
            pass
        request.session["thanks_kind"] = enquiry.kind
        return redirect("core:thank_you")
    return render(request, template, {"form": form})


def contact(request):
    return _enquiry(request, "contact", "core/contact.html")


def bulk_enquiry(request):
    initial = {}
    if request.user.is_authenticated:
        u = request.user
        initial = {"name": u.get_full_name(), "email": u.email, "phone": u.phone, "company": u.company_name, "gstin": u.gstin}
    initial["product_interest"] = request.GET.get("product", "")
    return _enquiry(request, "bulk", "core/bulk_enquiry.html", initial)


def thank_you(request):
    kind = request.session.pop("thanks_kind", None)
    if not kind:
        return redirect("core:contact")
    response = render(request, "core/thank_you.html", {"kind": kind})
    response["X-Robots-Tag"] = "noindex"
    return response


POLICIES = {
    "privacy": "Privacy policy",
    "terms": "Terms and conditions",
    "shipping-policy": "Shipping policy",
    "returns": "Returns and refunds",
}


def policy(request, slug):
    if slug not in POLICIES:
        return not_found(request, None)
    return render(request, "core/policy.html", {"slug": slug, "title": POLICIES[slug]})


def healthz(request):
    """Touches the database so a free-tier project never counts as inactive. Called daily by Vercel Cron."""
    from django.db import connection
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
    return HttpResponse("ok", content_type="text/plain", headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})


def robots(request):
    body = "User-agent: *\nAllow: /\nDisallow: /manage/\nDisallow: /account/\nDisallow: /cart/\nDisallow: /checkout/\nDisallow: /thank-you/\nDisallow: /healthz/\n"
    body += f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}\n"
    return HttpResponse(body, content_type="text/plain")


def not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)
