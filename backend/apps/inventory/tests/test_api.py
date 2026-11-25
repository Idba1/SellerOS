from decimal import Decimal

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.inventory.models import InventoryMovement, StockUnit
from tests.factories import FactoryContext, create_store_graph


class InventoryApiTests(APITestCase):
    def setUp(self):
        self.graph_a = create_store_graph(FactoryContext(namespace="inventory-api-a"))
        self.graph_b = create_store_graph(FactoryContext(namespace="inventory-api-b"))
        self.stock_unit_a = self.create_stock_unit(
            self.graph_a.store,
            name="Canvas Tote",
            quantity_on_hand=5,
            low_stock_threshold=5,
        )
        self.stock_unit_b = self.create_stock_unit(
            self.graph_b.store,
            name="Foreign Tote",
            quantity_on_hand=7,
        )
        self.opening_movement = InventoryMovement.objects.create(
            store=self.graph_a.store,
            stock_unit=self.stock_unit_a,
            movement_type=InventoryMovement.MovementType.OPENING_BALANCE,
            quantity_delta=5,
            created_by=self.graph_a.owner,
        )

    @staticmethod
    def create_stock_unit(store, *, name, quantity_on_hand, low_stock_threshold=None):
        product = Product.objects.create(
            store=store,
            name=name,
            selling_price=Decimal("100.00"),
            unit_cost=Decimal("20.00"),
        )
        return StockUnit.objects.create(
            store=store,
            product=product,
            quantity_on_hand=quantity_on_hand,
            low_stock_threshold=low_stock_threshold,
        )

    def authenticate(self, account):
        token = Token.objects.create(user=account)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_list_is_paginated_and_limited_to_the_current_store(self):
        self.authenticate(self.graph_a.owner)

        response = self.client.get(reverse("inventory-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["id"], str(self.stock_unit_a.pk))
        self.assertEqual(row["product_name"], "Canvas Tote")
        self.assertEqual(row["quantity_on_hand"], 5)
        self.assertEqual(row["low_stock_threshold"], 5)
        self.assertTrue(row["is_low_stock"])
        self.assertNotIn("store", row)
        self.assertNotIn(str(self.stock_unit_b.pk), str(response.data))

    def test_active_staff_can_read_same_store_movement_history(self):
        self.authenticate(self.graph_a.staff)

        response = self.client.get(
            reverse("inventory-movement-list", args=[self.stock_unit_a.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        movement = response.data["results"][0]
        self.assertEqual(movement["id"], str(self.opening_movement.pk))
        self.assertEqual(movement["stock_unit_id"], str(self.stock_unit_a.pk))
        self.assertEqual(movement["quantity_delta"], 5)
        self.assertNotIn("store", movement)

    def test_staff_manual_adjustment_uses_atomic_service(self):
        self.authenticate(self.graph_a.staff)

        response = self.client.post(
            reverse("inventory-manual-adjustment", args=[self.stock_unit_a.pk]),
            {"quantity_delta": -2, "reason": "Damaged packaging count"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["movement_type"],
            InventoryMovement.MovementType.MANUAL_ADJUSTMENT,
        )
        self.assertEqual(response.data["quantity_delta"], -2)
        self.assertEqual(response.data["reason"], "Damaged packaging count")
        self.assertNotIn("store", response.data)
        self.stock_unit_a.refresh_from_db()
        self.assertEqual(self.stock_unit_a.quantity_on_hand, 3)
        self.assertEqual(self.stock_unit_a.movements.count(), 2)

    def test_opening_balance_and_threshold_are_store_scoped_and_one_time(self):
        fresh = self.create_stock_unit(
            self.graph_a.store,
            name="Fresh Stock Tote",
            quantity_on_hand=0,
        )
        self.authenticate(self.graph_a.owner)

        threshold_response = self.client.patch(
            reverse("inventory-detail", args=[fresh.pk]),
            {"low_stock_threshold": 3},
            format="json",
        )
        opening_response = self.client.post(
            reverse("inventory-opening-balance", args=[fresh.pk]),
            {"quantity": 8},
            format="json",
        )
        repeat_response = self.client.post(
            reverse("inventory-opening-balance", args=[fresh.pk]),
            {"quantity": 1},
            format="json",
        )

        self.assertEqual(threshold_response.status_code, 200)
        self.assertEqual(threshold_response.data["low_stock_threshold"], 3)
        self.assertEqual(opening_response.status_code, 201)
        self.assertEqual(
            opening_response.data["movement_type"],
            InventoryMovement.MovementType.OPENING_BALANCE,
        )
        self.assertEqual(repeat_response.status_code, 400)
        fresh.refresh_from_db()
        self.assertEqual(fresh.quantity_on_hand, 8)
        self.assertEqual(fresh.movements.count(), 1)

    def test_validation_rejects_invalid_manual_payload_without_changes(self):
        self.authenticate(self.graph_a.owner)
        url = reverse("inventory-manual-adjustment", args=[self.stock_unit_a.pk])

        cases = (
            ({"quantity_delta": 0, "reason": "No change"}, "quantity_delta"),
            ({"quantity_delta": 1, "reason": "   "}, "reason"),
            (
                {
                    "quantity_delta": 1,
                    "reason": "Count correction",
                    "movement_type": "OPENING_BALANCE",
                },
                "movement_type",
            ),
        )
        for payload, field in cases:
            with self.subTest(payload=payload):
                response = self.client.post(url, payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["error"]["code"], "validation_error")
                self.assertIn(field, response.data["error"]["details"])

        overdraw_response = self.client.post(
            url,
            {"quantity_delta": -6, "reason": "Overdraw attempt"},
            format="json",
        )
        self.assertEqual(overdraw_response.status_code, 400)
        self.assertEqual(overdraw_response.data["error"]["code"], "validation_error")
        self.assertIn(
            "quantity_delta", overdraw_response.data["error"]["details"]
        )

        self.stock_unit_a.refresh_from_db()
        self.assertEqual(self.stock_unit_a.quantity_on_hand, 5)
        self.assertEqual(self.stock_unit_a.movements.count(), 1)

    def test_cross_store_history_and_adjustment_are_not_found_without_disclosure(self):
        self.authenticate(self.graph_a.owner)
        history_url = reverse("inventory-movement-list", args=[self.stock_unit_b.pk])
        adjustment_url = reverse("inventory-manual-adjustment", args=[self.stock_unit_b.pk])

        history_response = self.client.get(history_url)
        adjustment_response = self.client.post(
            adjustment_url,
            {"quantity_delta": 1, "reason": "Attempted foreign change"},
            format="json",
        )

        for response in (history_response, adjustment_response):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data["error"]["code"], "not_found")
            self.assertNotIn(str(self.stock_unit_b.pk), str(response.data))
            self.assertNotIn("Foreign Tote", str(response.data))

        self.stock_unit_b.refresh_from_db()
        self.assertEqual(self.stock_unit_b.quantity_on_hand, 7)
        self.assertFalse(self.stock_unit_b.movements.exists())

    def test_query_and_authentication_rules_fail_closed(self):
        unauthenticated_response = self.client.get(reverse("inventory-list"))
        self.assertEqual(unauthenticated_response.status_code, 401)
        self.assertEqual(
            unauthenticated_response.data["error"]["code"], "not_authenticated"
        )

        self.authenticate(self.graph_a.owner)
        response = self.client.get(
            f"{reverse('inventory-list')}?store_id={self.graph_b.store.pk}"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("store_id", response.data["error"]["details"])
