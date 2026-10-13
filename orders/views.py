import json
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.forms import AddressForm
from core.security import throttle_post, too_many
from core.constants import GSTIN_REGEX
from core.models import SiteSetting
from store.models import Product

from . import payments, pricing, services
from .cart import Cart
from .models import Order


def _methods(setting, total=None):
    methods = [("razorpay", "Pay online", "UPI, cards, netbanking and wallets via Razorpay")]
    if setting.cod_enabled and (total is None or total <= setting.cod_max_amount):
        methods.append(("cod", "Cash on delivery", f"₹{setting.cod_fee:.0f} handling fee. Orders up to ₹{setting.cod_max_amount:.0f}"))
    methods.append(("bank", "Bank transfer / UPI", "Pay manually. We dispatch once the payment reaches us"))
    return methods


def cart_view(request):
    cart = Cart(request)
    lines = cart.lines()
    setting = SiteSetting.load()
    state = request.user.addresses.first().state if request.user.is_authenticated and request.user.addresses.exists() else setting.seller_state
    totals = pricing.compute(lines, state, setting, wholesale=getattr(request.user, "is_wholesale", False))
    return render(request, "orders/cart.html", {"lines": lines, "totals": totals})


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product.objects.active(), pk=pk)
    size = request.POST.get("size") or product.size_list[0]
    if size not in product.size_list:
        messages.error(request, "Choose a size.")
        return redirect(product.get_absolute_url())
    try:
        qty = max(1, int(request.POST.get("quantity", 1)))
    except ValueError:
        qty = 1
    if not product.in_stock:
        messages.error(request, "This belt is out of stock. Send us a wholesale enquiry for a restock date.")
        return redirect(product.get_absolute_url())
    Cart(request).add(product, size, qty)
    if request.POST.get("buy_now"):
        return redirect("orders:checkout")
    messages.success(request, f"Added {product.name} (size {size}) to your cart.")
    return redirect("orders:cart")


@require_POST
def cart_update(request):
    cart = Cart(request)
    for key in list(cart.data):
        field = f"qty_{key}"
        if field in request.POST:
            try:
                cart.set_qty(key, int(request.POST[field]))
            except ValueError:
                pass
    return redirect("orders:cart")


@require_POST
def cart_remove(request):
    Cart(request).remove(request.POST.get("key", ""))
    return redirect("orders:cart")


@login_required
def checkout(request):
    cart = Cart(request)
    lines = cart.lines()
    if not lines:
        messages.info(request, "Your cart is empty.")
        return redirect("orders:cart")
    setting = SiteSetting.load()
    user = request.user
    addresses = list(user.addresses.all())
    default = next((a for a in addresses if a.is_default), addresses[0] if addresses else None)
    errors = []
    selected_addr = request.POST.get("address_id") or (str(default.pk) if default else "new")
    aform = AddressForm(request.POST if request.method == "POST" and selected_addr == "new" else None,
                        initial={"full_name": user.get_full_name(), "phone": user.phone})
    method = request.POST.get("payment_method", "razorpay")
    gstin = (request.POST.get("gstin", user.gstin if user.is_business else "")).strip().upper()

    if request.method == "POST":
        address = None
        if selected_addr == "new":
            if aform.is_valid():
                address = aform.save(commit=False)
                address.user = user
        else:
            address = next((a for a in addresses if str(a.pk) == selected_addr), None)
            if address is None:
                errors.append("Choose a delivery address.")
        if gstin and not re.fullmatch(GSTIN_REGEX, gstin):
            errors.append("Enter a valid 15-character GSTIN, or leave it blank.")
        t = pricing.compute(lines, address.state if address else None, setting, user.is_wholesale, method)
        if method not in dict((m[0], m) for m in _methods(setting, t["total"])):
            errors.append("That payment method is not available for this order.")
        if address and not errors:
            if address.pk is None:
                address.is_default = not addresses
                address.save()
            try:
                order = services.create_order(user, lines, address, method, gstin, request.POST.get("notes", "")[:500])
            except services.StockError as e:
                messages.error(request, str(e))
                return redirect("orders:cart")
            cart.clear()
            services.send_confirmation(order)
            if method == "razorpay":
                return redirect("orders:pay", number=order.order_number)
            return redirect("orders:success", number=order.order_number)
        if not address and selected_addr == "new" and not aform.is_valid():
            errors.append("Check the address fields below.")

    state = next((a.state for a in addresses if str(a.pk) == selected_addr), setting.seller_state)
    totals = pricing.compute(lines, state, setting, user.is_wholesale, method)
    return render(request, "orders/checkout.html", {
        "lines": lines, "totals": totals, "addresses": addresses, "selected_addr": selected_addr, "aform": aform,
        "methods": _methods(setting), "method": method, "gstin": gstin, "errors": errors, "setting": setting,
    })


@login_required
def quote(request):
    """Live order totals for the checkout page when the address or payment method changes."""
    lines = Cart(request).lines()
    setting = SiteSetting.load()
    state = request.GET.get("state") or setting.seller_state
    t = pricing.compute(lines, state, setting, request.user.is_wholesale, request.GET.get("method"))
    fmt = lambda v: f"₹{v:,.2f}"
    return JsonResponse({
        "subtotal": fmt(t["subtotal"]), "shipping": "Free" if not t["shipping"] else fmt(t["shipping"]),
        "cod_fee": fmt(t["cod_fee"]), "has_cod": bool(t["cod_fee"]), "total": fmt(t["total"]),
        "tax_label": "IGST" if not t["intra_state"] else "CGST + SGST", "tax": fmt(t["tax"]),
    })


@login_required
def pay(request, number):
    order = get_object_or_404(Order, order_number=number, user=request.user)
    if not order.can_pay_online:
        return redirect("orders:detail", number=number)
    ctx = {"order": order, "demo": payments.demo_mode()}
    if not ctx["demo"]:
        if not payments.is_configured():
            messages.error(request, "Online payments are not set up yet. Please call us to complete this order.")
            return redirect("orders:detail", number=number)
        try:
            ctx.update(rzp_order_id=payments.create_order(order), key_id=settings.RAZORPAY_KEY_ID, amount=int(order.total * 100))
        except Exception:
            messages.error(request, "We could not reach the payment gateway. Try again in a minute.")
            return redirect("orders:detail", number=number)
    return render(request, "orders/pay.html", ctx)


@login_required
@require_POST
def payment_verify(request):
    order = get_object_or_404(Order, razorpay_order_id=request.POST.get("razorpay_order_id", "x"), user=request.user)
    pid = request.POST.get("razorpay_payment_id", "")
    if payments.verify_signature(order.razorpay_order_id, pid, request.POST.get("razorpay_signature")):
        payments.mark_paid(order, pid)
        return redirect("orders:success", number=order.order_number)
    order.payment_status = "failed"
    order.save(update_fields=["payment_status", "updated"])
    messages.error(request, "Payment could not be verified. If money was deducted, it will be refunded automatically; contact us with your order number.")
    return redirect("orders:detail", number=order.order_number)


@login_required
@require_POST
def demo_pay(request, number):
    if not payments.demo_mode():
        return HttpResponse(status=404)
    order = get_object_or_404(Order, order_number=number, user=request.user)
    payments.mark_paid(order, f"demo_{order.pk}")
    return redirect("orders:success", number=number)


@csrf_exempt
@require_POST
def webhook(request):
    if not payments.verify_webhook(request.body, request.headers.get("X-Razorpay-Signature", "")):
        return HttpResponse(status=400)
    try:
        event = json.loads(request.body)
        entity = event["payload"]["payment"]["entity"]
        order = Order.objects.filter(razorpay_order_id=entity["order_id"]).first()
    except (KeyError, ValueError):
        return HttpResponse(status=200)
    if order and event.get("event") in ("payment.captured", "order.paid") and entity.get("amount") == int(order.total * 100):
        payments.mark_paid(order, entity.get("id", ""))
    elif order and event.get("event") == "payment.failed" and order.payment_status == "pending":
        order.payment_status = "failed"
        order.save(update_fields=["payment_status", "updated"])
    return HttpResponse(status=200)


def _own_order(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items"), order_number=number)
    if not (request.user.is_authenticated and (order.user_id == request.user.pk or request.user.is_staff)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return order


@login_required
def success(request, number):
    order = _own_order(request, number)
    return render(request, "orders/success.html", {"order": order, "setting": SiteSetting.load()})


@login_required
def order_list(request):
    qs = Order.objects.filter(user=request.user).prefetch_related("items")
    status = request.GET.get("status", "")
    if status in dict(Order.STATUS):
        qs = qs.filter(status=status)
    return render(request, "orders/order_list.html", {"orders": qs, "status": status, "statuses": Order.STATUS})


@login_required
def order_detail(request, number):
    return render(request, "orders/order_detail.html", {"order": _own_order(request, number), "setting": SiteSetting.load()})


@login_required
@require_POST
def order_cancel(request, number):
    order = _own_order(request, number)
    if order.can_cancel:
        services.cancel_order(order)
        messages.success(request, f"Order {order.order_number} cancelled.")
    else:
        messages.error(request, "This order can no longer be cancelled. Please call us.")
    return redirect("orders:detail", number=number)


@login_required
def invoice(request, number):
    return render(request, "orders/invoice.html", {"order": _own_order(request, number), "setting": SiteSetting.load()})


def track(request):
    order = None
    if request.method == "POST" and throttle_post(request, "track", 10, 900):
        return too_many()
    if request.method == "POST":
        number = request.POST.get("order_number", "").strip().upper()
        phone = re.sub(r"\D", "", request.POST.get("phone", ""))[-10:]
        order = Order.objects.filter(order_number=number, ship_phone=phone).first()
        if not order:
            messages.error(request, "No order matches that number and phone. Check both and try again.")
    return render(request, "orders/track.html", {"order": order})
