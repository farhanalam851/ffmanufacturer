from decimal import Decimal

from django.db import models

from .constants import STATE_CHOICES


class SiteSetting(models.Model):
    """One editable row that controls company details, shipping, GST and COD rules."""

    company_name = models.CharField(max_length=120, default="F.F Manufacturer")
    tagline = models.CharField(max_length=200, default="Premium leather belts for men and women")
    phone_primary = models.CharField(max_length=20, default="9889030693")
    phone_secondary = models.CharField(max_length=20, default="7007123854", blank=True)
    whatsapp_number = models.CharField(max_length=20, default="919889030693", help_text="Country code + number, no + sign")
    email = models.EmailField(default="orders@ffmanufacturer.example")
    address = models.CharField(max_length=250, default="Jajmau, Kanpur, Uttar Pradesh 208010")
    gstin = models.CharField("Company GSTIN", max_length=15, blank=True, help_text="Printed on every invoice")
    seller_state = models.CharField(max_length=60, choices=STATE_CHOICES, default="Uttar Pradesh",
                                    help_text="Same-state orders get CGST+SGST; other states get IGST")

    free_shipping_threshold = models.DecimalField("Free shipping above (retail)", max_digits=10, decimal_places=2, default=Decimal("2000"))
    b2b_free_shipping_threshold = models.DecimalField("Free shipping above (verified wholesale)", max_digits=10, decimal_places=2, default=Decimal("15000"))
    flat_shipping_charge = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("80"))
    outstation_surcharge = models.DecimalField("Extra charge outside seller state", max_digits=8, decimal_places=2, default=Decimal("40"))
    shipping_gst_rate = models.DecimalField("GST % on shipping and COD fee", max_digits=4, decimal_places=2, default=Decimal("18"))

    cod_enabled = models.BooleanField("Cash on delivery", default=True)
    cod_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("50"))
    cod_max_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("10000"))
    bank_details = models.TextField(blank=True, help_text="Shown to customers who choose bank transfer / UPI")

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Enquiry(models.Model):
    KIND = [("bulk", "Bulk / wholesale enquiry"), ("contact", "General contact")]
    STATUS = [("new", "New"), ("contacted", "Contacted"), ("won", "Converted"), ("closed", "Closed")]

    kind = models.CharField(max_length=10, choices=KIND, default="contact")
    name = models.CharField(max_length=100)
    company = models.CharField(max_length=150, blank=True)
    gstin = models.CharField(max_length=15, blank=True)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    product_interest = models.CharField(max_length=200, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS, default="new")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        verbose_name_plural = "enquiries"

    def __str__(self):
        return f"{self.get_kind_display()} from {self.name}"
