from django.urls import path

from .views import DashboardSummaryView, ProductPerformanceView, SalesSummaryView

urlpatterns = [
    path("dashboard/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("sales-summary/", SalesSummaryView.as_view(), name="sales-summary"),
    path(
        "product-performance/",
        ProductPerformanceView.as_view(),
        name="product-performance",
    ),
]
