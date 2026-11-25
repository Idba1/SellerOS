from django.urls import path

from .views import ProductDetailView, ProductListView, ProductVariantListView

urlpatterns = [
    path("", ProductListView.as_view(), name="product-list"),
    path("<uuid:product_id>/variants/", ProductVariantListView.as_view(), name="product-variant-list"),
    path("<uuid:product_id>/", ProductDetailView.as_view(), name="product-detail"),
]
