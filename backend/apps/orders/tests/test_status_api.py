from decimal import Decimal

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.inventory.models import InventoryMovement, StockUnit
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from tests.factories import FactoryContext, create_store_graph


class OrderStatusUpdateApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="order-status-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="order-status-b"))
        self.product_a = Product.objects.create(
            store=self.graph_a.store,
            name="Status Product A",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("30.00"),
        )
        self.product_b = Product.objects.create(
            store=self.graph_b.store,
            name="Status Product B",
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("30.00"),
        )
        self.stock_a = StockUnit.objects.create(
            store=self.graph_a.store,
            product=self.product_a,
            quantity_on_hand=5,
        )
        self.pending = self.create_order(
            self.graph_a.store, self.product_a, SalesOrder.Status.PENDING
        )
        self.foreign = self.create_order(
            self.graph_b.store, self.product_b, SalesOrder.Status.PENDING
        )

    @staticmethod
    def create_order(store, product, status):
        customer = Customer.objects.create(
            store=store,
            display_name=f"Synthetic {store.name} buyer",
        )
        order = SalesOrder.objects.create(
            store=store,
            customer=customer,
            status=status,
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name_snapshot=product.name,
            quantity=2,
            selling_price_snapshot=product.selling_price,
            unit_cost_snapshot=None,
        )
        return order

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def status_url(self, order):
        return reverse("order-status", args=[order.pk])

    def test_pending_confirmation_deducts_stock_and_returns_audit_evidence(self):
        self.authenticate(self.graph_a.staff)

        response = self.client.post(
            self.status_url(self.pending),
            {"status": SalesOrder.Status.CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["order"]["status"], SalesOrder.Status.CONFIRMED)
        self.assertEqual(
            response.data["status_event"]["from_status"], SalesOrder.Status.PENDING
        )
        self.assertEqual(
            response.data["status_event"]["to_status"], SalesOrder.Status.CONFIRMED
        )
        self.assertEqual(
            response.data["status_event"]["initiated_by_id"], str(self.graph_a.staff.pk)
        )
        self.stock_a.refresh_from_db()
        self.assertEqual(self.stock_a.quantity_on_hand, 3)
        movement = InventoryMovement.objects.get()
        self.assertEqual(movement.order_item.order_id, self.pending.pk)
        self.assertEqual(OrderStatusEvent.objects.count(), 1)

    def test_supported_no_effect_transition_records_a_second_event(self):
        self.authenticate(self.graph_a.owner)
        self.client.post(
            self.status_url(self.pending),
            {"status": SalesOrder.Status.CONFIRMED},
            format="json",
        )

        response = self.client.post(
            self.status_url(self.pending),
            {"status": SalesOrder.Status.PROCESSING},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["order"]["status"], SalesOrder.Status.PROCESSING)
        self.assertEqual(response.data["status_event"]["from_status"], SalesOrder.Status.CONFIRMED)
        self.assertEqual(response.data["status_event"]["to_status"], SalesOrder.Status.PROCESSING)
        self.assertEqual(OrderStatusEvent.objects.filter(order=self.pending).count(), 2)

    def test_unsafe_transition_fails_closed_without_an_audit_record(self):
        self.authenticate(self.graph_a.owner)
        self.client.post(
            self.status_url(self.pending),
            {"status": SalesOrder.Status.CONFIRMED},
            format="json",
        )

        response = self.client.post(
            self.status_url(self.pending),
            {"status": SalesOrder.Status.CANCELLED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("status", response.data["error"]["details"])
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, SalesOrder.Status.CONFIRMED)
        self.assertEqual(OrderStatusEvent.objects.filter(order=self.pending).count(), 1)
        self.stock_a.refresh_from_db()
        self.assertEqual(self.stock_a.quantity_on_hand, 3)

    def test_authentication_foreign_access_and_payload_validation_fail_closed(self):
        response = self.client.post(
            self.status_url(self.pending),
            {"status": SalesOrder.Status.CONFIRMED},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

        self.authenticate(self.graph_a.owner)
        foreign_response = self.client.post(
            self.status_url(self.foreign),
            {"status": SalesOrder.Status.CONFIRMED},
            format="json",
        )
        self.assertEqual(foreign_response.status_code, 404)
        self.assertNotIn(str(self.foreign.pk), str(foreign_response.data))

        invalid_status_response = self.client.post(
            self.status_url(self.pending),
            {"status": "UNKNOWN"},
            format="json",
        )
        self.assertEqual(invalid_status_response.status_code, 400)
        self.assertEqual(
            invalid_status_response.data["error"]["code"], "validation_error"
        )
        self.assertIn("status", invalid_status_response.data["error"]["details"])

        unknown_field_response = self.client.post(
            self.status_url(self.pending),
            {"status": SalesOrder.Status.CONFIRMED, "store_id": str(self.graph_b.store.pk)},
            format="json",
        )
        self.assertEqual(unknown_field_response.status_code, 400)
        self.assertIn("store_id", unknown_field_response.data["error"]["details"])
