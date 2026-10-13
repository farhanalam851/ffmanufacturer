import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from core.constants import GSTIN_REGEX

from .models import Address, User


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}))

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    class Meta:
        model = User
        fields = ["account_type", "first_name", "last_name", "email", "phone", "company_name", "gstin"]
        widgets = {"account_type": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["phone"].required = True
        self.fields["account_type"].initial = User.RETAIL
        self.fields["company_name"].help_text = "Business buyers only"
        self.fields["gstin"].help_text = "Needed for wholesale prices and GST invoices"

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists. Try logging in.")
        return email

    def clean_gstin(self):
        return self.cleaned_data.get("gstin", "").strip().upper()

    def clean(self):
        data = super().clean()
        if data.get("account_type") == User.BUSINESS:
            if not data.get("company_name"):
                self.add_error("company_name", "Enter your company name.")
            if not data.get("gstin"):
                self.add_error("gstin", "Enter your GSTIN to register as a business.")
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The two passwords do not match.")
        elif p1:
            try:
                password_validation.validate_password(p1)
            except forms.ValidationError as e:
                self.add_error("password1", e)
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "company_name", "gstin"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.is_business:
            del self.fields["company_name"]
            del self.fields["gstin"]

    def clean_gstin(self):
        g = self.cleaned_data.get("gstin", "").strip().upper()
        if g and not re.fullmatch(GSTIN_REGEX, g):
            raise forms.ValidationError("Enter a valid 15-character GSTIN.")
        return g

    def save(self, commit=True):
        # A changed GSTIN has to be verified again.
        if "gstin" in self.changed_data and self.instance.business_verified:
            self.instance.business_verified = False
        return super().save(commit)


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["full_name", "phone", "line1", "line2", "city", "state", "pincode", "is_default"]
