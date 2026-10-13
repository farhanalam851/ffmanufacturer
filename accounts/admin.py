from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm

from .models import Address, User


class AdminUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "first_name")

    def clean_password2(self):
        if self.cleaned_data.get("password1") != self.cleaned_data.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return self.cleaned_data["password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    ordering = ("-date_joined",)
    list_display = ("email", "first_name", "phone", "account_type", "company_name", "gstin", "business_verified", "is_staff")
    list_filter = ("account_type", "business_verified", "is_staff", "is_active")
    list_editable = ("business_verified",)
    search_fields = ("email", "first_name", "last_name", "phone", "company_name", "gstin")
    inlines = [AddressInline]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "phone")}),
        ("Business", {"fields": ("account_type", "company_name", "gstin", "business_verified")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "password1", "password2", "is_staff")}),
    )
    actions = ["verify_businesses"]

    @admin.action(description="Verify selected business accounts")
    def verify_businesses(self, request, queryset):
        n = queryset.filter(account_type="business").update(business_verified=True)
        self.message_user(request, f"{n} business account(s) verified.")
