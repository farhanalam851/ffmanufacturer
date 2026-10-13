from django.contrib import admin

from .models import Enquiry, SiteSetting


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Company", {"fields": ("company_name", "tagline", "phone_primary", "phone_secondary", "whatsapp_number", "email", "address")}),
        ("GST", {"fields": ("gstin", "seller_state", "shipping_gst_rate")}),
        ("Shipping", {"fields": ("free_shipping_threshold", "b2b_free_shipping_threshold", "flat_shipping_charge", "outstation_surcharge")}),
        ("Payment", {"fields": ("cod_enabled", "cod_fee", "cod_max_amount", "bank_details")}),
    )

    def has_add_permission(self, request):
        return not SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "company", "phone", "quantity", "status", "created")
    list_filter = ("kind", "status")
    list_editable = ("status",)
    search_fields = ("name", "company", "phone", "email")
    date_hierarchy = "created"
