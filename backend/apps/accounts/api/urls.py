from django.urls import path

from .views import CurrentAccountView, LoginView, RegistrationView

urlpatterns = [
    path("register/", RegistrationView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("me/", CurrentAccountView.as_view(), name="auth-current-account"),
]
