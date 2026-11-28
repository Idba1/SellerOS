from django.urls import path

from .views import (
    CurrentAccountView,
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegistrationView,
)

urlpatterns = [
    path("register/", RegistrationView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("me/", CurrentAccountView.as_view(), name="auth-current-account"),
]
