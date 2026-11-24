from django.urls import path

from .views import OrderDetailView, OrderListView

urlpatterns = [
    path("", OrderListView.as_view(), name="order-list"),
    path("<uuid:order_id>/", OrderDetailView.as_view(), name="order-detail"),
]
