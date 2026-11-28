"""Validation and public payloads for registration and token login."""
from uuid import UUID

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.models import Account
from .tokens import password_reset_token_generator

_DUMMY_PASSWORD_HASH = make_password("selleros-auth-timing-placeholder")
_INVALID_CREDENTIALS_MESSAGE = "Unable to log in with provided credentials."


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("id", "email")
        read_only_fields = fields


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        email = Account.objects.normalize_email(value)
        if Account.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        return value

    def create(self, validated_data):
        try:
            return Account.objects.create_user(**validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        except IntegrityError:
            raise serializers.ValidationError(
                {"email": ["An account with this email already exists."]}
            ) from None


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = Account.objects.normalize_email(attrs["email"])
        account = Account.objects.filter(email__iexact=email).first()

        if account is None:
            check_password(attrs["password"], _DUMMY_PASSWORD_HASH)
            raise AuthenticationFailed(_INVALID_CREDENTIALS_MESSAGE)
        if not account.is_active or not account.check_password(attrs["password"]):
            raise AuthenticationFailed(_INVALID_CREDENTIALS_MESSAGE)

        attrs["account"] = account
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Accept an email without revealing whether it belongs to an account."""

    email = serializers.EmailField(max_length=254)

    def validate_email(self, value):
        return Account.objects.normalize_email(value)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=128, trim_whitespace=True)
    token = serializers.CharField(max_length=256, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    default_error_messages = {
        "invalid_link": "This password reset link is invalid or has expired.",
    }

    def validate(self, attrs):
        try:
            account_id = UUID(force_str(urlsafe_base64_decode(attrs["uid"])))
        except (TypeError, ValueError, OverflowError, UnicodeDecodeError):
            self.fail("invalid_link")

        account = Account.objects.filter(pk=account_id, is_active=True).first()
        if account is None or not password_reset_token_generator.check_token(
            account, attrs["token"]
        ):
            self.fail("invalid_link")

        try:
            validate_password(attrs["password"], user=account)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error

        attrs["account"] = account
        return attrs
