import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import Order, OrderItem


class ItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "name", "sku", "size", "quantity", "unit_price", "gst_rate", "taxable_value", "tax_amount", "line_total")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "total", "payment_method", "payment_status", "status", "ship_state", "created")
    list_filter = ("status", "payment_status", "payment_method", "ship_state")
    list_editable = ("status", "payment_status")
    search_fields = ("order_number", "user__email", "ship_name", "ship_phone", "gstin", "tracking_number")
    date_hierarchy = "created"
    inlines = [ItemInline]
    readonly_fields = ("order_number", "razorpay_order_id", "razorpay_payment_id", "paid_at", "created")
    actions = ["export_csv"]

    @admin.action(description="Export selected orders to CSV")
    def export_csv(self, request, queryset):
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="orders.csv"'
        w = csv.writer(resp)
        w.writerow(["Order", "Date", "Customer", "GSTIN", "State", "Taxable", "CGST", "SGST", "IGST", "Total", "Payment", "Status"])
        for o in queryset:
            w.writerow([o.order_number, o.created.date(), o.user.email, o.gstin, o.ship_state, o.taxable_value, o.cgst, o.sgst, o.igst, o.total, o.get_payment_status_display(), o.get_status_display()])
        return resp
