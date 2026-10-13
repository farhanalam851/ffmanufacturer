from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.models import Enquiry
from orders import services
from orders.models import Order, OrderItem
from store.models import Product, Review

User = get_user_model()
staff_required = user_passes_test(lambda u: u.is_active and u.is_staff, login_url="accounts:login")


@staff_required
def overview(request):
    today = timezone.localdate()
    live = Order.objects.exclude(status="cancelled")
    start = today - timedelta(days=13)
    by_day = {
        r["d"]: r["s"]
        for r in live.filter(created__date__gte=start).annotate(d=TruncDate("created")).values("d").annotate(s=Sum("total"))
    }
    days = [start + timedelta(days=i) for i in range(14)]
    values = [by_day.get(d, Decimal("0")) for d in days]
    peak = max(values) or Decimal("1")
    chart = [{"label": d.strftime("%d %b"), "value": v, "pct": max(3, int(v / peak * 100)) if v else 0} for d, v in zip(days, values)]
    top = (
        OrderItem.objects.exclude(order__status="cancelled").values("product__name", "product__sku")
        .annotate(units=Sum("quantity"), revenue=Sum("line_total")).order_by("-units")[:5]
    )
    month_start = today.replace(day=1)
    ctx = {
        "kpis": {
            "sales_30": live.filter(created__date__gte=today - timedelta(days=30)).aggregate(t=Sum("total"))["t"] or 0,
            "sales_month": live.filter(created__date__gte=month_start).aggregate(t=Sum("total"))["t"] or 0,
            "collected": Order.objects.filter(payment_status="paid").aggregate(t=Sum("total"))["t"] or 0,
            "orders_open": Order.objects.filter(status__in=["pending", "confirmed", "processing"]).count(),
            "customers": User.objects.filter(is_staff=False).count(),
            "to_verify": User.objects.filter(account_type="business", business_verified=False).count(),
            "new_enquiries": Enquiry.objects.filter(status="new").count(),
            "reviews": Review.objects.count(),
        },
        "chart": chart, "top": top,
        "by_status": {k: Order.objects.filter(status=k).count() for k, _ in Order.STATUS},
        "recent": Order.objects.select_related("user")[:8],
        "low_stock": Product.objects.filter(stock__lte=10, is_active=True).order_by("stock")[:8],
    }
    return render(request, "dashboard/overview.html", ctx)


@staff_required
def order_list(request):
    qs = Order.objects.select_related("user")
    status, pay, q = request.GET.get("status", ""), request.GET.get("payment", ""), request.GET.get("q", "").strip()
    if status in dict(Order.STATUS):
        qs = qs.filter(status=status)
    if pay in dict(Order.PAYMENT_STATUS):
        qs = qs.filter(payment_status=pay)
    if q:
        qs = qs.filter(Q(order_number__icontains=q) | Q(user__email__icontains=q) | Q(ship_name__icontains=q) | Q(ship_phone__icontains=q) | Q(gstin__icontains=q))
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "dashboard/order_list.html", {
        "page": page, "status": status, "payment": pay, "q": q, "statuses": Order.STATUS, "pay_statuses": Order.PAYMENT_STATUS,
    })


@staff_required
def order_detail(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items").select_related("user"), order_number=number)
    if request.method == "POST":
        new_status = request.POST.get("status", order.status)
        new_pay = request.POST.get("payment_status", order.payment_status)
        if new_status in dict(Order.STATUS) and new_pay in dict(Order.PAYMENT_STATUS):
            if new_status == "cancelled" and order.status != "cancelled":
                services.cancel_order(order)
                order.refresh_from_db()
            else:
                order.status = new_status
            order.payment_status = new_pay
            if new_pay == "paid" and not order.paid_at:
                order.paid_at = timezone.now()
            order.courier = request.POST.get("courier", "").strip()[:60]
            order.tracking_number = request.POST.get("tracking_number", "").strip()[:60]
            if new_status == "shipped" and not order.shipped_at:
                order.shipped_at = timezone.now()
                order.save()
                services.email_customer(
                    order, f"Order {order.order_number} has shipped",
                    f"Hello {order.user.first_name},\n\nYour order is on its way via {order.courier or 'courier'}"
                    f"{' (tracking ' + order.tracking_number + ')' if order.tracking_number else ''}.\n\nF.F Manufacturer",
                )
            else:
                order.save()
            messages.success(request, "Order updated.")
        return redirect("dashboard:order_detail", number=number)
    return render(request, "dashboard/order_detail.html", {"order": order, "statuses": Order.STATUS, "pay_statuses": Order.PAYMENT_STATUS})


@staff_required
def enquiries(request):
    if request.method == "POST":
        enq = get_object_or_404(Enquiry, pk=request.POST.get("id"))
        if request.POST.get("status") in dict(Enquiry.STATUS):
            enq.status = request.POST["status"]
            enq.save(update_fields=["status"])
        return redirect(request.get_full_path())
    status = request.GET.get("status", "")
    qs = Enquiry.objects.all()
    if status in dict(Enquiry.STATUS):
        qs = qs.filter(status=status)
    return render(request, "dashboard/enquiries.html", {"enquiries": qs[:100], "status": status, "statuses": Enquiry.STATUS})


@staff_required
def customers(request):
    qs = User.objects.filter(is_staff=False).annotate(order_count=Count("orders"), spent=Sum("orders__total", filter=~Q(orders__status="cancelled")))
    kind = request.GET.get("type", "")
    if kind in ("retail", "business"):
        qs = qs.filter(account_type=kind)
    if request.GET.get("pending") == "1":
        qs = qs.filter(account_type="business", business_verified=False)
    page = Paginator(qs.order_by("-date_joined"), 25).get_page(request.GET.get("page"))
    return render(request, "dashboard/customers.html", {"page": page, "kind": kind, "pending": request.GET.get("pending") == "1"})


@staff_required
@require_POST
def verify_business(request, pk):
    user = get_object_or_404(User, pk=pk, account_type="business")
    user.business_verified = request.POST.get("verify") == "1"
    user.save(update_fields=["business_verified"])
    messages.success(request, f"{user.company_name or user.email} {'verified' if user.business_verified else 'unverified'}.")
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, request.get_host()):
        return redirect(nxt)
    return redirect("dashboard:customers")
