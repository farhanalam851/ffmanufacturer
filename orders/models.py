import uuid

from django.conf import settings
from django.db import models

from store.models import Product


class Order(models.Model):
    STATUS = [
        ("pending", "Awaiting payment"), ("confirmed", "Confirmed"), ("processing", "Processing"),
        ("shipped", "Shipped"), ("delivered", "Delivered"), ("cancelled", "Cancelled"),
    ]
    PAYMENT_STATUS = [("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed"), ("refunded", "Refunded")]
    METHODS = [("razorpay", "Online (UPI, cards, netbanking)"), ("cod", "Cash on delivery"), ("bank", "Bank transfer / UPI")]

    order_number = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=12, choices=STATUS, default="pending")

    # Address snapshot, so later edits to the address book never change an old invoice
    ship_name = models.CharField(max_length=100)
    ship_phone = models.CharField(max_length=10)
    ship_line1 = models.CharField(max_length=150)
    ship_line2 = models.CharField(max_length=150, blank=True)
    ship_city = models.CharField(max_length=80)
    ship_state = models.CharField(max_length=60)
    ship_pincode = models.CharField(max_length=6)
    company_name = models.CharField(max_length=150, blank=True)
    gstin = models.CharField("Buyer GSTIN", max_length=15, blank=True)
    notes = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cod_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxable_value = models.DecimalField(max_digits=12, decimal_places=2)
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    payment_method = models.CharField(max_length=10, choices=METHODS)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default="pending")
    razorpay_order_id = models.CharField(max_length=60, blank=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=60, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    courier = models.CharField(max_length=60, blank=True)
    tracking_number = models.CharField(max_length=60, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.order_number or f"Order #{self.pk}"

    def save(self, *args, **kwargs):
        is_new = not self.order_number
        if is_new:
            self.order_number = "TMP" + uuid.uuid4().hex[:15]  # replaced right below, keeps the unique index happy
        super().save(*args, **kwargs)
        if is_new:
            self.order_number = f"FF{self.created:%y%m}{self.pk:05d}"
            super().save(update_fields=["order_number"])

    @property
    def is_intra_state(self):
        return self.igst == 0

    @property
    def tax_total(self):
        return self.cgst + self.sgst + self.igst

    @property
    def handling_total(self):
        return self.shipping_charge + self.cod_fee

    @property
    def timeline(self):
        steps = ["pending", "confirmed", "processing", "shipped", "delivered"]
        labels = ["Placed", "Confirmed", "Processing", "Shipped", "Delivered"]
        idx = steps.index(self.status) if self.status in steps else -1
        return [(label, i <= idx) for i, label in enumerate(labels)]

    @property
    def can_cancel(self):
        return self.status in ("pending", "confirmed") and self.payment_status != "paid"

    @property
    def can_pay_online(self):
        return self.payment_method == "razorpay" and self.payment_status in ("pending", "failed") and self.status != "cancelled"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    name = models.CharField(max_length=160)
    sku = models.CharField(max_length=40)
    hsn_code = models.CharField(max_length=10, blank=True)
    size = models.CharField(max_length=20, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=4, decimal_places=2)
    taxable_value = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} × {self.name}"
