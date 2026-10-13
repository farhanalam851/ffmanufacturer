from django.urls import path

from . import views

app_name = "store"
urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("category/<slug:slug>/", views.catalog, name="category"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/toggle/<int:pk>/", views.wishlist_toggle, name="wishlist_toggle"),
    path("<slug:slug>/", views.product_detail, name="product"),
    path("<slug:slug>/review/", views.review_add, name="review_add"),
]
