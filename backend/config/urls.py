from django.urls import path

from core.health import health, readiness

urlpatterns = [
    path("health/", health, name="health"),
    path("ready/", readiness, name="readiness"),
]
