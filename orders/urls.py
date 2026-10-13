from django.urls import path

from . import views

app_name = "orders"
urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/remove/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/quote/", views.quote, name="quote"),
    path("payment/verify/", views.payment_verify, name="verify"),
    path("payment/webhook/", views.webhook, name="webhook"),
    path("payment/<str:number>/", views.pay, name="pay"),
    path("payment/<str:number>/demo/", views.demo_pay, name="demo_pay"),
    path("orders/", views.order_list, name="list"),
    path("orders/track/", views.track, name="track"),
    path("orders/<str:number>/", views.order_detail, name="detail"),
    path("orders/<str:number>/success/", views.success, name="success"),
    path("orders/<str:number>/cancel/", views.order_cancel, name="cancel"),
    path("orders/<str:number>/invoice/", views.invoice, name="invoice"),
]
