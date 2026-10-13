from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.SiteLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("addresses/", views.addresses, name="addresses"),
    path("addresses/add/", views.address_edit, name="address_add"),
    path("addresses/<int:pk>/edit/", views.address_edit, name="address_edit"),
    path("addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),
    path("password/change/", auth_views.PasswordChangeView.as_view(
        template_name="accounts/form_page.html", success_url=reverse_lazy("accounts:profile"),
        extra_context={"title": "Change password", "back": "accounts:profile"}), name="password_change"),
    path("password/reset/", views.ThrottledPasswordResetView.as_view(
        template_name="accounts/form_page.html", email_template_name="registration/password_reset_email.txt",
        subject_template_name="registration/password_reset_subject.txt",
        success_url=reverse_lazy("accounts:password_reset_done"),
        extra_context={"title": "Reset your password", "back": "accounts:login", "submit": "Email reset link"}), name="password_reset"),
    path("password/reset/sent/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/message_page.html",
        extra_context={"title": "Check your email", "body": "If an account exists for that address, a reset link is on its way."}), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/form_page.html", success_url=reverse_lazy("accounts:password_reset_complete"),
        extra_context={"title": "Choose a new password", "submit": "Save password"}), name="password_reset_confirm"),
    path("password/reset/complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/message_page.html",
        extra_context={"title": "Password updated", "body": "You can now log in with your new password.", "link": "accounts:login", "link_text": "Log in"}), name="password_reset_complete"),
]
