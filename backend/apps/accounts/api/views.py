"""Public registration/login and token-validated current-account views."""
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import AccountSerializer, LoginSerializer, RegistrationSerializer
from .tokens import rotate_token


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
