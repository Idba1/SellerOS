"""Explicit PostgreSQL test mode; credentials must be exported, not read from .env."""
from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "testserver"]
