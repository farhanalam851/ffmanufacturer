from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.security import throttle_post, too_many
from orders.models import Order
from store.models import Wishlist

from .forms import AddressForm, EmailLoginForm, ProfileForm, RegisterForm


class SiteLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    initial = {"account_type": "business"} if request.GET.get("type") == "business" else {}
    if request.method == "POST" and throttle_post(request, "register", 10, 3600):
        return too_many("Too many sign-ups from this connection. Please try again later.")
    form = RegisterForm(request.POST if request.method == "POST" else None, initial=initial)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        if user.is_business:
            messages.success(request, "Account created. We will verify your GSTIN shortly; wholesale prices unlock once it is approved.")
        else:
            messages.success(request, "Welcome to F.F Manufacturer. Your account is ready.")
        nxt = request.GET.get("next", "")
        if nxt and url_has_allowed_host_and_scheme(nxt, request.get_host()):
            return redirect(nxt)
        return redirect("accounts:dashboard")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    orders = Order.objects.filter(user=request.user)
    stats = {
        "orders": orders.count(),
        "spent": orders.exclude(status="cancelled").aggregate(t=Sum("total"))["t"] or 0,
        "open": orders.exclude(status__in=["delivered", "cancelled"]).count(),
        "wishlist": Wishlist.objects.filter(user=request.user).count(),
    }
    unpaid = orders.filter(payment_status="pending", payment_method="razorpay").exclude(status="cancelled")[:3]
    return render(request, "accounts/dashboard.html", {
        "stats": stats, "recent": orders.prefetch_related("items")[:5], "unpaid": unpaid,
    })


@login_required
def profile(request):
    form = ProfileForm(request.POST if request.method == "POST" else None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def addresses(request):
    return render(request, "accounts/addresses.html", {"addresses": request.user.addresses.all()})


@login_required
def address_edit(request, pk=None):
    instance = get_object_or_404(request.user.addresses, pk=pk) if pk else None
    form = AddressForm(request.POST if request.method == "POST" else None, instance=instance)
    if request.method == "POST" and form.is_valid():
        addr = form.save(commit=False)
        addr.user = request.user
        if not request.user.addresses.exists():
            addr.is_default = True
        addr.save()
        messages.success(request, "Address saved.")
        return redirect("accounts:addresses")
    return render(request, "accounts/form_page.html", {"form": form, "title": "Edit address" if pk else "Add address", "back": "accounts:addresses"})


@login_required
@require_POST
def address_delete(request, pk):
    get_object_or_404(request.user.addresses, pk=pk).delete()
    messages.success(request, "Address removed.")
    return redirect("accounts:addresses")


class ThrottledPasswordResetView(auth_views.PasswordResetView):
    """Limit reset e-mails per connection so the form cannot be used to spam inboxes."""

    def post(self, request, *args, **kwargs):
        if throttle_post(request, "pwreset", 5, 3600):
            return too_many("Too many reset requests. Please try again in an hour.")
        return super().post(request, *args, **kwargs)
