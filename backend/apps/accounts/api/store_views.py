"""Create and read the authenticated account's current store profile."""
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Account, Store, StoreMembership
from core.api.query import validate_query_parameters
from core.permissions import require_authorized_store

from .store_serializers import StoreCreateSerializer, StoreProfileSerializer


class CurrentStoreProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        validate_query_parameters(request.query_params, set())
        store = require_authorized_store(request.user)
        return Response(StoreProfileSerializer(store).data)

    def post(self, request):
        serializer = StoreCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            account = Account.objects.select_for_update().get(pk=request.user.pk)
            if Store.objects.filter(owner=account).exists():
                raise ValidationError(
                    {"non_field_errors": ["This account already owns a store."]}
                )
            if StoreMembership.objects.filter(account=account).exists():
                raise PermissionDenied("Staff accounts cannot create a store.")
            store = serializer.save(owner=account)

        return Response(StoreProfileSerializer(store).data, status=status.HTTP_201_CREATED)
