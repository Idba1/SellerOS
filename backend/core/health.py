"""Public liveness and minimal database readiness; never return error details."""
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


@never_cache
@require_safe
def health(request):
    return JsonResponse({"status": "ok"})


@never_cache
@require_safe
def readiness(request):
    database = connections.databases.get("default", {})
    engine = database.get("ENGINE", "")
    if not engine or engine == "django.db.backends.dummy":
        database_status = "not_configured"
    else:
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                database_status = "ok" if cursor.fetchone() == (1,) else "unavailable"
        except Exception:
            # All dependency failures are generic, including driver/config errors.
            database_status = "unavailable"
    ready = database_status == "ok"
    return JsonResponse(
        {"status": "ready" if ready else "not_ready",
         "checks": {"app": "ok", "database": database_status}},
        status=200 if ready else 503,
    )
