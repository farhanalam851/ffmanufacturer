from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count, Q
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    gender = models.CharField(max_length=10, choices=[("men", "Men"), ("women", "Women"), ("unisex", "Unisex")], default="unisex")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:category", args=[self.slug])


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True, category__is_active=True)

    def with_rating(self):
        ok = Q(reviews__is_approved=True)
        return self.annotate(avg_rating=Avg("reviews__rating", filter=ok), review_count=Count("reviews", filter=ok, distinct=True))


class Product(models.Model):
    GENDERS = [("men", "Men"), ("women", "Women"), ("unisex", "Unisex")]

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    sku = models.CharField("SKU", max_length=40, unique=True)
    gender = models.CharField(max_length=10, choices=GENDERS, default="men")
    short_description = models.CharField(max_length=220, blank=True)
    description = models.TextField(blank=True)
    material = models.CharField(max_length=120, default="Genuine leather")
    color = models.CharField(max_length=60, blank=True)
    buckle = models.CharField("Buckle finish", max_length=80, blank=True)
    sizes = models.CharField(max_length=120, blank=True, help_text="Comma separated waist sizes in inches, e.g. 30,32,34,36,38,40. Leave blank for free size.")
    image = models.ImageField(upload_to="products/")

    price = models.DecimalField("MRP (incl. GST)", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("1"))])
    sale_price = models.DecimalField("Sale price (incl. GST)", max_digits=10, decimal_places=2, null=True, blank=True)
    gst_rate = models.DecimalField("GST %", max_digits=4, decimal_places=2, default=Decimal("18"), help_text="Confirm the correct rate for your HSN code with your CA")
    hsn_code = models.CharField("HSN code", max_length=10, default="4203")
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:170]
            slug, n = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:product", args=[self.slug])

    @property
    def retail_price(self):
        return self.sale_price if self.sale_price and self.sale_price < self.price else self.price

    @property
    def discount_percent(self):
        if self.retail_price < self.price:
            return int(round((self.price - self.retail_price) / self.price * 100))
        return 0

    @property
    def size_list(self):
        return [s.strip() for s in self.sizes.split(",") if s.strip()] or ["Free size"]

    @property
    def in_stock(self):
        return self.stock > 0

    def unit_price(self, qty, user=None):
        """Retail price, or the matching wholesale tier for verified business accounts."""
        price = self.retail_price
        if user is not None and getattr(user, "is_authenticated", False) and user.is_wholesale:
            eligible = [t for t in self.tiers.all() if qty >= t.min_qty]
            if eligible:
                best = max(eligible, key=lambda t: t.min_qty)
                price = min(price, best.price)
        return price


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="gallery")
    image = models.ImageField(upload_to="products/gallery/")
    alt = models.CharField(max_length=120, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]


class WholesaleTier(models.Model):
    """Per-piece price once a verified business buys at least min_qty of this product."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="tiers")
    min_qty = models.PositiveIntegerField(validators=[MinValueValidator(2)])
    price = models.DecimalField("Price per piece (incl. GST)", max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["min_qty"]
        unique_together = ("product", "min_qty")

    def __str__(self):
        return f"{self.product.name}: {self.min_qty}+ pcs at {self.price}"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=100, blank=True)
    comment = models.TextField(max_length=1500)
    photo = models.ImageField(upload_to="reviews/", blank=True)
    is_approved = models.BooleanField(default=True, help_text="Untick to hide a review")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        unique_together = ("product", "user")

    def __str__(self):
        return f"{self.rating}★ {self.product} by {self.user}"


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created"]
