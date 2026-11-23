"""Store-owned catalogue records with optional named variants."""
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from apps.accounts.models import Store, UUIDTimeStampedModel


class Product(UUIDTimeStampedModel):
    """A store-owned catalogue product with a current seller-entered price/cost."""

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=80, null=True, blank=True, default=None)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    has_variants = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(selling_price__gt=0),
                name="catalog_product_selling_price_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_cost__gte=0) | models.Q(unit_cost__isnull=True),
                name="catalog_product_unit_cost_nonnegative_or_null",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "A product name is required."})

        if self.category is not None:
            self.category = self.category.strip() or None

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ProductVariant(UUIDTimeStampedModel):
    """A named option for a variant-based product; product fields remain canonical."""

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="variants",
    )
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "product",
                name="catalog_variant_product_name_ci_unique",
            )
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "A variant name is required."})
        if self.product_id and not self.product.has_variants:
            raise ValidationError(
                {"product": "Variants require a product with has_variants=True."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
