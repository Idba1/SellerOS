from django.urls import path

from .views import (
    InventoryListView,
    InventoryMovementListView,
    ManualStockAdjustmentView,
    OpeningBalanceView,
    StockUnitDetailView,
)

urlpatterns = [
    path("", InventoryListView.as_view(), name="inventory-list"),
    path("<uuid:stock_unit_id>/", StockUnitDetailView.as_view(), name="inventory-detail"),
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
    path(
        "<uuid:stock_unit_id>/opening-balance/",
        OpeningBalanceView.as_view(),
        name="inventory-opening-balance",
    ),
]
