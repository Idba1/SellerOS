from django.urls import include, path

from core.health import health, readiness

urlpatterns = [
    path("api/v1/auth/", include("apps.accounts.api.urls")),
    path("health/", health, name="health"),
    path("ready/", readiness, name="readiness"),
]
