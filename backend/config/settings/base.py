"""Shared Django settings with validated PostgreSQL configuration."""
import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from apps.ai.providers.configuration import load_llm_provider_policy
from core.database import postgres_database

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY.strip():
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be supplied in the environment.")
if SECRET_KEY.strip() == "REPLACE_ME":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must not use the example placeholder.")

# Provider policy contains no API key. PLAN-06 currently permits no provider
# execution or spend; any non-disabled LLM environment configuration fails closed.
LLM_PROVIDER_POLICY = load_llm_provider_policy(os.environ)

INSTALLED_APPS = [
    "core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.catalog.apps.CatalogConfig",
    "apps.customers.apps.CustomersConfig",
    "apps.inventory.apps.InventoryConfig",
    "apps.orders.apps.OrdersConfig",
    "apps.expenses.apps.ExpensesConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.segmentation.apps.SegmentationConfig",
    "apps.forecast.apps.ForecastConfig",
    "apps.assistant.apps.AssistantConfig",
    "rest_framework",
    "rest_framework.authtoken",
]
AUTH_USER_MODEL = "accounts.Account"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "core.api.exceptions.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "core.api.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": "3/hour",
        "auth_login": "5/min",
        "auth_password_reset": "3/hour",
        "assistant_draft": "10/hour",
    },
}
PASSWORD_RESET_FRONTEND_URL = os.environ.get(
    "PASSWORD_RESET_FRONTEND_URL", "http://127.0.0.1:5173/reset-password"
).strip()
_password_reset_url = urlparse(PASSWORD_RESET_FRONTEND_URL)
if (
    _password_reset_url.scheme not in {"http", "https"}
    or not _password_reset_url.netloc
    or _password_reset_url.username
    or _password_reset_url.password
    or _password_reset_url.query
    or _password_reset_url.fragment
    or _password_reset_url.path.rstrip("/") != "/reset-password"
):
    raise ImproperlyConfigured(
        "PASSWORD_RESET_FRONTEND_URL must be an HTTP(S) /reset-password URL without credentials, query, or fragment."
    )
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@selleros.invalid").strip()
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost").strip()
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "false").strip().lower() == "true"
# Context construction performs only local, store-scoped retrieval. Exceeding
# this bound discards the result and records a safe unavailable outcome.
ASSISTANT_CONTEXT_BUILD_MAX_SECONDS = 2.0
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": postgres_database(os.environ)}
USE_TZ = True
# Technical Django default, not the business date-grouping policy (PLAN-03 DR-07).
TIME_ZONE = "UTC"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# URLs do not serve media; uploads/static collection are not implemented yet.
