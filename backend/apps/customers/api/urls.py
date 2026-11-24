from django.urls import path

from apps.segmentation.api.views import CustomerSegmentView

from .views import CustomerDetailView, CustomerListView, CustomerPurchaseHistoryView

urlpatterns = [
    path("", CustomerListView.as_view(), name="customer-list"),
    path(
        "<uuid:customer_id>/purchase-history/",
        CustomerPurchaseHistoryView.as_view(),
        name="customer-purchase-history",
    ),
    path(
        "<uuid:customer_id>/segment/",
        CustomerSegmentView.as_view(),
        name="customer-segment",
    ),
    path("<uuid:customer_id>/", CustomerDetailView.as_view(), name="customer-detail"),
]
