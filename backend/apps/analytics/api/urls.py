from django.urls import path

from .views import ProductPerformanceView, SalesSummaryView

urlpatterns = [
    path("sales-summary/", SalesSummaryView.as_view(), name="sales-summary"),
    path(
        "product-performance/",
        ProductPerformanceView.as_view(),
        name="product-performance",
    ),
]
