from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("wholesale/", views.bulk_enquiry, name="bulk_enquiry"),
    path("thank-you/", views.thank_you, name="thank_you"),
    path("policies/<slug:slug>/", views.policy, name="policy"),
    path("healthz/", views.healthz, name="healthz"),
    path("robots.txt", views.robots, name="robots"),
]
