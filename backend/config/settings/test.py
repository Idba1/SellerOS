"""Explicit database-free test mode with debug disabled."""
from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "testserver"]
