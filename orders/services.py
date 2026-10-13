from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F

from core.models import SiteSetting
from store.models import Product

from . import pricing
from .models import Order, OrderItem


class StockError(Exception):
    pass


@transaction.atomic
def create_order(user, lines, address, method, gstin="", notes=""):
    setting = SiteSetting.load()
    locked = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[l["product"].pk for l in lines])}
    for l in lines:
        p = locked.get(l["product"].pk)
        if not p or not p.is_active or p.stock < l["qty"]:
            raise StockError(f"Only {p.stock if p else 0} left of {l['product'].name}. Please update your cart.")
    t = pricing.compute(lines, address.state, setting, wholesale=user.is_wholesale, method=method)
    order = Order.objects.create(
        user=user, ship_name=address.full_name, ship_phone=address.phone, ship_line1=address.line1,
        ship_line2=address.line2, ship_city=address.city, ship_state=address.state, ship_pincode=address.pincode,
        company_name=user.company_name if user.is_business else "", gstin=gstin, notes=notes,
        subtotal=t["subtotal"], shipping_charge=t["shipping"], cod_fee=t["cod_fee"], taxable_value=t["taxable"],
        cgst=t["cgst"], sgst=t["sgst"], igst=t["igst"], total=t["total"], payment_method=method,
        status="pending" if method == "razorpay" else "confirmed",
    )
    OrderItem.objects.bulk_create([
        OrderItem(order=order, product=l["product"], name=l["product"].name, sku=l["product"].sku,
                  hsn_code=l["product"].hsn_code, size=l["size"], quantity=l["qty"], unit_price=l["unit_price"],
                  gst_rate=l["product"].gst_rate, taxable_value=l["taxable"], tax_amount=l["tax"], line_total=l["line_total"])
        for l in lines
    ])
    for l in lines:
        p = locked[l["product"].pk]
        p.stock -= l["qty"]
        p.save(update_fields=["stock", "updated"])
    return order


@transaction.atomic
def cancel_order(order):
    for item in order.items.select_related("product"):
        Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
    order.status = "cancelled"
    order.save(update_fields=["status", "updated"])


def email_customer(order, subject, body):
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [order.user.email], fail_silently=True)
    except Exception:
        pass


def send_confirmation(order):
    email_customer(
        order, f"Order {order.order_number} received",
        f"Hello {order.user.first_name},\n\nThank you for your order {order.order_number} (total ₹{order.total}).\n"
        f"Payment: {order.get_payment_method_display()} - {order.get_payment_status_display()}.\n\nF.F Manufacturer, Jajmau, Kanpur",
    )
