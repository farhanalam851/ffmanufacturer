from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage, Review, WholesaleTier, Wishlist


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "gender", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


class GalleryInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class TierInline(admin.TabularInline):
    model = WholesaleTier
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("thumb", "name", "sku", "category", "price", "sale_price", "stock", "is_active", "is_featured")
    list_editable = ("price", "sale_price", "stock", "is_active", "is_featured")
    list_filter = ("category", "gender", "is_active", "is_featured")
    search_fields = ("name", "sku", "color")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [TierInline, GalleryInline]
    save_on_top = True

    @admin.display(description="")
    def thumb(self, obj):
        return format_html('<img src="{}" style="height:44px;width:44px;object-fit:cover;border-radius:6px">', obj.image.url) if obj.image else ""


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_approved", "created")
    list_editable = ("is_approved",)
    list_filter = ("rating", "is_approved")
    search_fields = ("product__name", "user__email", "comment")


admin.site.register(Wishlist)
