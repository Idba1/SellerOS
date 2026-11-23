"""Validation and public payloads for registration and token login."""
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.models import Account

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
