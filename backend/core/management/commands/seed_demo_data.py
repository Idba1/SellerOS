"""Load the reviewed synthetic SellerOS demo graph into a disposable test DB."""
import json
import secrets
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.accounts.models import Account, Store, StoreMembership
from apps.catalog.models import Product, ProductVariant
from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.inventory.models import InventoryMovement, StockUnit
from apps.orders.models import OrderItem, OrderStatusEvent, SalesOrder
from apps.orders.serializers import OrderCreateSerializer
from apps.orders.services import create_and_confirm_order, transition_order_status


SYNTHETIC_LABEL = "SYNTHETIC DATA — NOT SELLER PERFORMANCE"
CATALOG_FIXTURE_ID = "selleros-synthetic-catalog-customers-v1"
TIME_SERIES_FIXTURE_ID = "selleros-synthetic-orders-expenses-timeseries-v1"
DEMO_OWNER_EMAILS = {
    "synthetic-store-a": "synthetic-demo-owner-a@example.test",
    "synthetic-store-b": "synthetic-demo-owner-b@example.test",
}
DEMO_STAFF_EMAIL = "synthetic-demo-staff-a@example.test"
DEMO_ACCOUNT_EMAILS = tuple(DEMO_OWNER_EMAILS.values()) + (DEMO_STAFF_EMAIL,)
SEEDABLE_ORDER_KEYS = {
    "order-a-delivered-normal",
    "order-a-delivered-missing-cost",
    "order-b-delivered-sparse",
}


class Command(BaseCommand):
    help = "Reset and load reviewed synthetic demo records into a Django test database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Explicitly remove the previously generated synthetic demo graph first.",
        )

    def handle(self, *args, **options):
        if not options["reset"]:
            raise CommandError("Use --reset to explicitly rebuild synthetic demo records.")
        self._require_disposable_test_database()
        catalog, time_series = self._load_reviewed_manifests()

        with transaction.atomic():
            self._delete_existing_demo_graph()
            summary = self._seed_graph(catalog, time_series)

        self.stdout.write(self.style.WARNING(SYNTHETIC_LABEL))
        self.stdout.write(
            self.style.SUCCESS(
                "Loaded synthetic demo graph: "
                f"{summary['stores']} stores, {summary['products']} products, "
                f"{summary['customers']} customers, {summary['orders']} delivered orders, "
                f"and {summary['expenses']} expenses."
            )
        )

    @staticmethod
    def _require_disposable_test_database():
        database_name = str(connection.settings_dict["NAME"])
        if not settings.DEBUG or not database_name.startswith("test_"):
            raise CommandError(
                "Synthetic demo reset is permitted only when DEBUG=True on a Django "
                "test database. It will not run against a local, shared, or production database."
            )

    @staticmethod
    def _load_reviewed_manifests():
        sample_directory = Path(settings.BASE_DIR).parent / "data" / "sample"
        try:
            catalog = json.loads(
                (sample_directory / "synthetic-catalog-customers.v1.json").read_text(
                    encoding="utf-8"
                )
            )
            time_series = json.loads(
                (
                    sample_directory / "synthetic-orders-expenses-timeseries.v1.json"
                ).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise CommandError("Reviewed synthetic demo manifests could not be loaded.") from error

        if (
            catalog.get("fixture_id") != CATALOG_FIXTURE_ID
            or time_series.get("fixture_id") != TIME_SERIES_FIXTURE_ID
            or catalog.get("provenance") != "synthetic"
            or time_series.get("provenance") != "synthetic"
            or catalog.get("label") != SYNTHETIC_LABEL
            or time_series.get("label") != SYNTHETIC_LABEL
            or time_series.get("catalog_fixture_id") != CATALOG_FIXTURE_ID
        ):
            raise CommandError("Synthetic demo manifest provenance validation failed.")
        return catalog, time_series

    @staticmethod
    def _delete_existing_demo_graph():
        stores = list(
            Store.objects.filter(owner__email__in=DEMO_OWNER_EMAILS.values())
        )
        if not stores:
            return

        InventoryMovement.objects.filter(store__in=stores).delete()
        OrderStatusEvent.objects.filter(order__store__in=stores).delete()
        OrderItem.objects.filter(order__store__in=stores).delete()
        SalesOrder.objects.filter(store__in=stores).delete()
        StockUnit.objects.filter(store__in=stores).delete()
        Expense.objects.filter(store__in=stores).delete()
        Customer.objects.filter(store__in=stores).delete()
        ProductVariant.objects.filter(product__store__in=stores).delete()
        Product.objects.filter(store__in=stores).delete()
        StoreMembership.objects.filter(store__in=stores).delete()
        Store.objects.filter(pk__in=[store.pk for store in stores]).delete()
        Account.objects.filter(email__in=DEMO_ACCOUNT_EMAILS).delete()

    def _seed_graph(self, catalog, time_series):
        stores, owners = self._create_stores(catalog["stores"])
        self._create_staff(stores["synthetic-store-a"])
        products, variants = self._create_products(catalog["products"], stores)
        customers = self._create_customers(catalog["customers"], stores)
        self._create_expenses(time_series["expense_records"], stores, owners)
        orders = self._create_supported_delivered_orders(
            time_series["order_cases"],
            stores,
            owners,
            products,
            variants,
            customers,
        )
        return {
            "stores": len(stores),
            "products": len(products),
            "customers": len(customers),
            "orders": len(orders),
            "expenses": len(time_series["expense_records"]),
        }

    @staticmethod
    def _create_account(email):
        return Account.objects.create_user(email, secrets.token_urlsafe(32))

    def _create_stores(self, fixture_stores):
        stores, owners = {}, {}
        for fixture in fixture_stores:
            fixture_key = fixture["fixture_key"]
            owner = self._create_account(DEMO_OWNER_EMAILS[fixture_key])
            store = Store.objects.create(
                owner=owner,
                name=fixture["name"],
                timezone="Asia/Dhaka",
            )
            stores[fixture_key] = store
            owners[fixture_key] = owner
        return stores, owners

    def _create_staff(self, store):
        staff = self._create_account(DEMO_STAFF_EMAIL)
        StoreMembership.objects.create(store=store, account=staff)

    @staticmethod
    def _create_products(fixture_products, stores):
        products, variants = {}, {}
        for fixture in fixture_products:
            product = Product.objects.create(
                store=stores[fixture["store_key"]],
                name=fixture["name"],
                category=fixture["category"],
                selling_price=Decimal(fixture["selling_price"]),
                unit_cost=(
                    Decimal(fixture["unit_cost"])
                    if fixture["unit_cost"] is not None
                    else None
                ),
                has_variants=fixture["has_variants"],
                is_active=fixture["is_active"],
            )
            products[fixture["fixture_key"]] = product
            if fixture["has_variants"]:
                for variant_fixture in fixture["variants"]:
                    variant = ProductVariant.objects.create(
                        product=product,
                        name=variant_fixture["name"],
                        is_active=variant_fixture["is_active"],
                    )
                    variants[variant_fixture["fixture_key"]] = variant
                    StockUnit.objects.create(
                        store=product.store,
                        product=product,
                        variant=variant,
                        quantity_on_hand=10,
                    )
            else:
                StockUnit.objects.create(
                    store=product.store,
                    product=product,
                    quantity_on_hand=10,
                )
        return products, variants

    @staticmethod
    def _create_customers(fixture_customers, stores):
        customers = {}
        for fixture in fixture_customers:
            customer = Customer.objects.create(
                store=stores[fixture["store_key"]],
                display_name=fixture["display_name"],
                email=fixture["email"],
                phone=fixture["phone"],
            )
            customers[fixture["fixture_key"]] = customer
        return customers

    @staticmethod
    def _create_expenses(fixture_expenses, stores, owners):
        for fixture in fixture_expenses:
            Expense.objects.create(
                store=stores[fixture["store_key"]],
                description=fixture["description"],
                category=fixture["category"],
                amount=Decimal(fixture["amount"]),
                incurred_on=datetime.fromisoformat(fixture["incurred_on"]).date(),
                recorded_by=owners[fixture["store_key"]],
            )

    def _create_supported_delivered_orders(
        self,
        fixture_orders,
        stores,
        owners,
        products,
        variants,
        customers,
    ):
        orders = []
        for fixture in fixture_orders:
            if fixture["fixture_key"] not in SEEDABLE_ORDER_KEYS:
                continue
            store_key = fixture["store_key"]
            serializer = OrderCreateSerializer(
                data={
                    "customer_id": str(customers[fixture["customer_key"]].pk),
                    "items": [
                        {
                            "product_id": str(products[line["product_key"]].pk),
                            "variant_id": (
                                str(variants[line["variant_key"]].pk)
                                if line["variant_key"] is not None
                                else None
                            ),
                            "quantity": line["quantity"],
                        }
                        for line in fixture["lines"]
                    ],
                    "order_discount": fixture["order_discount"],
                    "seller_delivery_cost": fixture["seller_delivery_cost"],
                },
                context={"store": stores[store_key]},
            )
            if not serializer.is_valid():
                raise CommandError("A reviewed synthetic order fixture is invalid.")
            order = create_and_confirm_order(
                serializer=serializer,
                created_by=owners[store_key],
            )
            for status in ("PROCESSING", "SHIPPED", "DELIVERED"):
                order, _ = transition_order_status(
                    order_id=order.pk,
                    to_status=status,
                    initiated_by=owners[store_key],
                )
            self._apply_fixture_event_times(order, fixture["status_events"])
            orders.append(order)
        return orders

    @staticmethod
    def _apply_fixture_event_times(order, fixture_events):
        event_times = {
            event["status"]: datetime.fromisoformat(event["occurred_at"])
            for event in fixture_events
        }
        for event in order.status_events.all():
            occurred_at = event_times[event.to_status]
            OrderStatusEvent.objects.filter(pk=event.pk).update(
                occurred_at=occurred_at,
                created_at=occurred_at,
                updated_at=occurred_at,
            )

        confirmed_at = event_times["CONFIRMED"]
        delivered_at = event_times["DELIVERED"]
        SalesOrder.objects.filter(pk=order.pk).update(
            created_at=confirmed_at,
            updated_at=delivered_at,
            confirmed_at=confirmed_at,
            delivered_at=delivered_at,
        )
