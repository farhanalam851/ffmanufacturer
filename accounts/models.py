from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models

from core.constants import GSTIN_REGEX, STATE_CHOICES

phone_validator = RegexValidator(r"^[6-9][0-9]{9}$", "Enter a 10-digit Indian mobile number.")
gstin_validator = RegexValidator(GSTIN_REGEX, "Enter a valid 15-character GSTIN.")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create(email, password, **extra)


class User(AbstractUser):
    RETAIL, BUSINESS = "retail", "business"
    ACCOUNT_TYPES = [(RETAIL, "Individual buyer"), (BUSINESS, "Business / wholesale buyer")]

    username = None
    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=10, blank=True, validators=[phone_validator])
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default=RETAIL)
    company_name = models.CharField(max_length=150, blank=True)
    gstin = models.CharField("GSTIN", max_length=15, blank=True, validators=[gstin_validator])
    business_verified = models.BooleanField(
        default=False, help_text="Tick after checking the GSTIN. Unlocks wholesale tier prices."
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]
    objects = UserManager()

    @property
    def is_business(self):
        return self.account_type == self.BUSINESS

    @property
    def is_wholesale(self):
        return self.is_business and self.business_verified

    def __str__(self):
        return self.email


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=10, validators=[phone_validator])
    line1 = models.CharField("Address line 1", max_length=150)
    line2 = models.CharField("Address line 2", max_length=150, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=60, choices=STATE_CHOICES, default="Uttar Pradesh")
    pincode = models.CharField(max_length=6, validators=[RegexValidator(r"^[1-9][0-9]{5}$", "Enter a 6-digit PIN code.")])
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "-id"]
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.full_name}, {self.city} {self.pincode}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
