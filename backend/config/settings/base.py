"""Shared skeleton settings; database and business timezone remain unconfigured."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from core.database import postgres_database

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY.strip():
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be supplied in the environment.")
if SECRET_KEY.strip() == "REPLACE_ME":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must not use the example placeholder.")

INSTALLED_APPS = ["core.apps.CoreConfig", "rest_framework"]
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # Fail closed until the separately planned authentication foundation exists.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "core.api.exceptions.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "core.api.pagination.StandardPagination",
    "PAGE_SIZE": 20,
}
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
