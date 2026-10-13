from django.urls import path

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.overview, name="overview"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<str:number>/", views.order_detail, name="order_detail"),
    path("enquiries/", views.enquiries, name="enquiries"),
    path("customers/", views.customers, name="customers"),
    path("customers/<int:pk>/verify/", views.verify_business, name="verify_business"),
]
