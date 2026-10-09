from django.test import SimpleTestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from core.api.pagination import StandardPagination
from core.api.query import validate_query_parameters


class ListFixture(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        validate_query_parameters(request.query_params, {"page", "page_size", "category"})
        items = [{"id": str(i), "category": "a" if i % 2 else "b"} for i in range(1, 26)]
        category = request.query_params.get("category")
        if category:
            items = [item for item in items if item["category"] == category]
        pagination = StandardPagination()
        page = pagination.paginate_queryset(items, request, view=self)
        return pagination.get_paginated_response(page)


class PermissionFixture(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise PermissionDenied()


class ContractTests(SimpleTestCase):
    def request(self, query=""):
        return ListFixture.as_view()(APIRequestFactory().get("/api/v1/products/" + query))

    def test_pagination_and_filter_shape(self):
        response = self.request()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIn("/api/v1/products/?page=2", response.data["next"])
        filtered = self.request("?category=a&page_size=2")
        self.assertEqual(filtered.data["count"], 13)
        self.assertTrue(all(item["category"] == "a" for item in filtered.data["results"]))

    def test_invalid_filter_duplicate_and_size_errors(self):
        for query in ("?store_id=foreign", "?category=a&category=b", "?page_size=0", "?page_size=101", "?page_size=" + "9" * 5000):
            with self.subTest(query=query):
                response = self.request(query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")

    def test_invalid_page_and_permission_contract(self):
        response = self.request("?page=999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "not_found")
        denied = PermissionFixture.as_view()(APIRequestFactory().get("/api/v1/fixture/"))
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.data["error"]["code"], "permission_denied")
