from django.urls import include, path

from core.health import health, readiness

urlpatterns = [
    path("api/v1/auth/", include("apps.accounts.api.urls")),
    path("api/v1/stores/", include("apps.accounts.api.store_urls")),
    path("api/v1/products/", include("apps.catalog.api.urls")),
    path("api/v1/inventory/", include("apps.inventory.api.urls")),
    path("health/", health, name="health"),
    path("ready/", readiness, name="readiness"),
]
