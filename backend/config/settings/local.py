"""Loopback-only development configuration."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from core.environment import load_local_env

load_local_env(Path(__file__).resolve().parents[2] / ".env")

from .base import *  # noqa: E402,F403

_debug = os.environ.get("DJANGO_DEBUG", "false").strip().lower()
if _debug not in {"true", "false"}:
    raise ImproperlyConfigured("DJANGO_DEBUG must be true or false.")
DEBUG = _debug == "true"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
