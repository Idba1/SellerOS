from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.orders.models import OrderItem, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class CustomerSegmentApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="segment-api-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="segment-api-b"))
        self.customer = Customer.objects.create(
            store=self.graph_a.store, display_name="Synthetic Segment API Buyer"
        )
        self.foreign_customer = Customer.objects.create(
            store=self.graph_b.store, display_name="Foreign Segment Buyer"
        )
        self.product = Product.objects.create(
            store=self.graph_a.store,
            name="Segment API Product",
            selling_price=Decimal("5000.00"),
            unit_cost=Decimal("100.00"),
        )
        self.as_of = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)
        token = Token.objects.create(user=self.graph_a.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def segment_url(self, customer=None, **query):
        url = reverse("customer-segment", args=[(customer or self.customer).pk])
        return f"{url}?{urlencode(query)}" if query else url

    def seed_order(self, *, delivered_at, price):
        order = SalesOrder.objects.create(
            store=self.graph_a.store,
            customer=self.customer,
            status=SalesOrder.Status.DELIVERED,
            delivered_at=delivered_at,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name_snapshot="Segment API Product",
            quantity=1,
            selling_price_snapshot=price,
            unit_cost_snapshot=Decimal("100.00"),
        )

    def test_returns_explainable_high_value_assignment_from_same_store_facts(self):
        self.seed_order(
            delivered_at=datetime(2026, 6, 20, tzinfo=timezone.utc),
            price=Decimal("6000.00"),
        )
        self.seed_order(
            delivered_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
            price=Decimal("4000.00"),
        )

        response = self.client.get(self.segment_url(as_of=self.as_of.isoformat()))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["segment"], "HIGH_VALUE")
        self.assertEqual(response.data["rule_version"], "segment-v1")
        self.assertEqual(response.data["store_timezone"], "Asia/Dhaka")
        self.assertEqual(
            response.data["values"],
            {
                "recorded_purchase_count": 2,
                "last_recorded_purchase_at": "2026-06-30T00:00:00Z",
                "recency_days": 1,
                "trailing_365_day_spend_bdt": "10000.00",
            },
        )
        self.assertIn("high-value rule", response.data["explanation"])
        self.assertNotIn("Synthetic Segment API Buyer", str(response.data))

    def test_requires_aware_as_of_and_hides_foreign_customer(self):
        missing = self.client.get(self.segment_url())
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.data["error"]["code"], "validation_error")
        self.assertIn("as_of", missing.data["error"]["details"])

        naive = self.client.get(self.segment_url(as_of="2026-07-01T12:00:00"))
        self.assertEqual(naive.status_code, 400)
        self.assertIn("as_of", naive.data["error"]["details"])

        foreign = self.client.get(
            self.segment_url(self.foreign_customer, as_of=self.as_of.isoformat())
        )
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.data["error"]["code"], "not_found")
        self.assertNotIn(str(self.foreign_customer.pk), str(foreign.data))
        self.assertNotIn("Foreign Segment Buyer", str(foreign.data))

    def test_unauthenticated_and_unknown_query_are_rejected(self):
        self.client.credentials()
        unauthenticated = self.client.get(self.segment_url(as_of=self.as_of.isoformat()))
        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(unauthenticated.data["error"]["code"], "not_authenticated")

        token = Token.objects.get(user=self.graph_a.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        unknown_query = self.client.get(
            self.segment_url(as_of=self.as_of.isoformat(), store_id="attempt")
        )
        self.assertEqual(unknown_query.status_code, 400)
        self.assertEqual(unknown_query.data["error"]["code"], "validation_error")
        self.assertIn("store_id", unknown_query.data["error"]["details"])
