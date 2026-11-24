from django.urls import path

from .views import (
    InventoryListView,
    InventoryMovementListView,
    ManualStockAdjustmentView,
)

urlpatterns = [
    path("", InventoryListView.as_view(), name="inventory-list"),
    path(
        "<uuid:stock_unit_id>/movements/",
        InventoryMovementListView.as_view(),
        name="inventory-movement-list",
    ),
    path(
        "<uuid:stock_unit_id>/adjustments/",
        ManualStockAdjustmentView.as_view(),
        name="inventory-manual-adjustment",
    ),
]
