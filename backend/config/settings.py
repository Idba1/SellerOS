"""Minimal local skeleton; no business database or authentication yet."""
import os

from django.core.exceptions import ImproperlyConfigured

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY.strip():
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be supplied in the environment.")
if SECRET_KEY.strip() == "REPLACE_ME":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must not use the example placeholder.")

DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
INSTALLED_APPS = ["core.apps.CoreConfig"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
# Django's dummy backend: PostgreSQL configuration is a later task.
DATABASES = {}
USE_TZ = True
