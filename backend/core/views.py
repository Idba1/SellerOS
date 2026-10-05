from django.http import JsonResponse
from django.views.decorators.http import require_safe


@require_safe
def health(request):
    """Public process liveness only; no database or seller data access."""
    return JsonResponse({"status": "ok"})
