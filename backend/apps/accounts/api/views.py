"""Public account access, recovery, and token-validated account views."""
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import Account
from .serializers import (
    AccountSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegistrationSerializer,
)
from .tokens import password_reset_token_generator, rotate_token


def auth_response(account, token, response_status=status.HTTP_200_OK):
    return Response(
        {"account": AccountSerializer(account).data, "token": token.key},
        status=response_status,
    )


class RegistrationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            account = serializer.save()
            token = rotate_token(account)
        return auth_response(account, token, status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    def get_authenticate_header(self, request):
        # The public credential endpoint still returns a standards-compliant
        # 401 for invalid credentials without attempting bearer-token login.
        return "Token"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = rotate_token(serializer.validated_data["account"])
        return auth_response(serializer.validated_data["account"], token)


class CurrentAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AccountSerializer(request.user).data)


class PasswordResetRequestView(APIView):
    """Issue a reset email without disclosing account existence or state."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = (
            Account.objects.filter(email__iexact=serializer.validated_data["email"], is_active=True)
            .first()
        )
        if account is not None:
            query = urlencode(
                {
                    "uid": urlsafe_base64_encode(force_bytes(account.pk)),
                    "token": password_reset_token_generator.make_token(account),
                }
            )
            reset_url = f"{settings.PASSWORD_RESET_FRONTEND_URL}?{query}"
            # Delivery failures remain indistinguishable from an unknown email.
            # This protects account enumeration; local development uses Django's
            # console backend so the generated link is visible to the operator.
            send_mail(
                subject="Reset your SellerOS password",
                message=(
                    "A password reset was requested for your SellerOS account.\n\n"
                    f"Set a new password: {reset_url}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[account.email],
                fail_silently=True,
            )
        return Response(
            {"detail": "If an active account matches this email, a reset link has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(APIView):
    """Set a new validated password and revoke existing API sessions."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            account = Account.objects.select_for_update().get(
                pk=serializer.validated_data["account"].pk
            )
            account.set_password(serializer.validated_data["password"])
            account.save(update_fields=["password", "updated_at"])
            Token.objects.filter(user=account).delete()
        return Response({"detail": "Your password has been reset. Please sign in."})
