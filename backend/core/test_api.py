from django.http import Http404
from django.test import SimpleTestCase
from rest_framework import serializers
from rest_framework.exceptions import Throttled
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from core.api.exceptions import exception_handler


class InputSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class ValidationView(APIView):
    permission_classes = [AllowAny]  # Test fixture only; never registered as a URL.

    def post(self, request):
        serializer = InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)


class MissingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise Http404


class ApiBaselineTests(SimpleTestCase):
    def test_validation_keeps_field_details(self):
        response = ValidationView.as_view()(
            APIRequestFactory().post("/fixture", {"quantity": 0}, format="json")
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("quantity", response.data["error"]["details"])

    def test_not_found_shape(self):
        response = MissingView.as_view()(APIRequestFactory().get("/fixture"))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "not_found")
        self.assertIn("detail", response.data["error"]["details"])

    def test_default_permission_denies_anonymous(self):
        response = APIView.as_view()(APIRequestFactory().get("/fixture"))
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

    def test_preserves_retry_header_and_does_not_expose_unhandled_error(self):
        response = exception_handler(Throttled(wait=5), {})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "5")
        self.assertIsNone(exception_handler(RuntimeError("private internals"), {}))
