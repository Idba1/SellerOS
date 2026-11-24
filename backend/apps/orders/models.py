"""Minimum recorded-order persistence required for derived customer history."""
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.accounts.models import Store, StoreMembership, UUIDTimeStampedModel
from apps.catalog.models import Product, ProductVariant
from apps.customers.models import Customer


class SalesOrder(UUIDTimeStampedModel):
    """A store sale with lifecycle facts; transitions remain a later workflow."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PROCESSING = "PROCESSING", "Processing"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"
        RETURN_REQUESTED = "RETURN_REQUESTED", "Return requested"
        RETURNED = "RETURNED", "Returned"
        REFUNDED = "REFUNDED", "Refunded"

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="sales_orders",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="sales_orders",
        null=True,
        blank=True,
        default=None,
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    currency_code = models.CharField(max_length=3, default="BDT")
    order_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    seller_delivery_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    confirmed_at = models.DateTimeField(null=True, blank=True, default=None)
    delivered_at = models.DateTimeField(null=True, blank=True, default=None)
    cancelled_at = models.DateTimeField(null=True, blank=True, default=None)
    return_requested_at = models.DateTimeField(null=True, blank=True, default=None)
    returned_at = models.DateTimeField(null=True, blank=True, default=None)
    refunded_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(currency_code="BDT"),
                name="orders_sales_order_currency_bdt",
            ),
            models.CheckConstraint(
                condition=models.Q(order_discount__gte=0),
                name="orders_sales_order_discount_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(seller_delivery_cost__gte=0)
                | models.Q(seller_delivery_cost__isnull=True),
                name="orders_sales_order_delivery_cost_nonnegative_or_null",
            ),
        ]

    def __str__(self):
        return f"{self.status} order {self.pk}"

    def clean(self):
        super().clean()
        if isinstance(self.currency_code, str):
            self.currency_code = self.currency_code.strip().upper()
        if self.currency_code != "BDT":
            raise ValidationError({"currency_code": "SellerOS uses BDT in this prototype."})
        if (
            self.customer_id
            and self.store_id
            and self.customer.store_id != self.store_id
        ):
            raise ValidationError({"customer": "Customer must belong to the order store."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class OrderItem(models.Model):
    """An order line with snapshots preserved from later catalogue changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    order = models.ForeignKey(
        SalesOrder,
        on_delete=models.PROTECT,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="order_items",
        null=True,
        blank=True,
        default=None,
    )
    product_name_snapshot = models.CharField(max_length=160)
    variant_name_snapshot = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        default=None,
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    selling_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
    )
    discount_allocation = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="orders_order_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(selling_price_snapshot__gt=0),
                name="orders_order_item_selling_price_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_cost_snapshot__gte=0)
                | models.Q(unit_cost_snapshot__isnull=True),
                name="orders_order_item_cost_nonnegative_or_null",
            ),
            models.CheckConstraint(
                condition=models.Q(discount_allocation__gte=0),
                name="orders_order_item_discount_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()
        if isinstance(self.product_name_snapshot, str):
            self.product_name_snapshot = self.product_name_snapshot.strip()
        if not self.product_name_snapshot:
            raise ValidationError(
                {"product_name_snapshot": "A product name snapshot is required."}
            )
        if isinstance(self.variant_name_snapshot, str):
            self.variant_name_snapshot = self.variant_name_snapshot.strip() or None

        if (
            self.order_id
            and self.product_id
            and self.order.store_id != self.product.store_id
        ):
            raise ValidationError({"product": "Product must belong to the order store."})
        if self.variant_id:
            if not self.product.has_variants:
                raise ValidationError(
                    {"variant": "Standalone products cannot use an order variant."}
                )
            if self.variant.product_id != self.product_id:
                raise ValidationError(
                    {"variant": "Variant must belong to the selected product."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class OrderStatusEvent(UUIDTimeStampedModel):
    """Immutable evidence of one accepted order status transition."""

    order = models.ForeignKey(
        SalesOrder,
        on_delete=models.PROTECT,
        related_name="status_events",
    )
    from_status = models.CharField(max_length=24, choices=SalesOrder.Status.choices)
    to_status = models.CharField(max_length=24, choices=SalesOrder.Status.choices)
    initiated_by = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="order_status_events",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(from_status=models.F("to_status")),
                name="orders_status_event_status_changed",
            )
        ]

    def clean(self):
        super().clean()
        if self.order_id and self.initiated_by_id:
            is_owner = self.order.store.owner_id == self.initiated_by_id
            is_active_staff = StoreMembership.objects.filter(
                store_id=self.order.store_id,
                account_id=self.initiated_by_id,
                is_active=True,
            ).exists()
            if not is_owner and not is_active_staff:
                raise ValidationError(
                    {"initiated_by": "Actor must have active order-store access."}
                )

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                {"non_field_errors": ["Order status events are immutable."]}
            )
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            {"non_field_errors": ["Order status events cannot be deleted."]}
        )
