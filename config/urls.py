from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core.sitemaps import SITEMAPS

admin.site.site_header = "F.F Manufacturer Admin"
admin.site.site_title = "F.F Manufacturer"
admin.site.index_title = "Store management"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("account/", include("accounts.urls")),
    path("shop/", include("store.urls")),
    path("manage/", include("dashboard.urls")),
    path("", include("orders.urls")),
    path("", include("core.urls")),
]

handler404 = "core.views.not_found"
handler500 = "core.views.server_error"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
