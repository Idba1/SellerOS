"""Shared skeleton settings; database and business timezone remain unconfigured."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY.strip():
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be supplied in the environment.")
if SECRET_KEY.strip() == "REPLACE_ME":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must not use the example placeholder.")

INSTALLED_APPS = ["core.apps.CoreConfig"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {}
USE_TZ = True
# Technical Django default, not the business date-grouping policy (PLAN-03 DR-07).
TIME_ZONE = "UTC"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# URLs do not serve media; uploads/static collection are not implemented yet.
