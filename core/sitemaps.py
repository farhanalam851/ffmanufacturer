from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from store.models import Category, Product


class StaticSitemap(Sitemap):
    priority = 0.5

    def items(self):
        return ["core:home", "core:about", "core:contact", "core:bulk_enquiry", "store:catalog"]

    def location(self, item):
        return reverse(item)


class PolicySitemap(Sitemap):
    priority = 0.3

    def items(self):
        return ["privacy", "terms", "shipping-policy", "returns"]

    def location(self, item):
        return reverse("core:policy", args=[item])


class ProductSitemap(Sitemap):
    priority = 0.8

    def items(self):
        return Product.objects.active()

    def lastmod(self, obj):
        return obj.updated


class CategorySitemap(Sitemap):
    priority = 0.7

    def items(self):
        return Category.objects.filter(is_active=True)


SITEMAPS = {"policies": PolicySitemap, "static": StaticSitemap, "products": ProductSitemap, "categories": CategorySitemap}
