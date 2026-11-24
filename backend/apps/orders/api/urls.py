from django.urls import path

from .views import OrderDetailView, OrderListView, OrderStatusUpdateView

urlpatterns = [
    path("", OrderListView.as_view(), name="order-list"),
    path("<uuid:order_id>/status/", OrderStatusUpdateView.as_view(), name="order-status"),
    path("<uuid:order_id>/", OrderDetailView.as_view(), name="order-detail"),
]
