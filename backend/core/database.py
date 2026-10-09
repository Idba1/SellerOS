"""Validate PostgreSQL environment without including credential values in errors."""
import re

from django.core.exceptions import ImproperlyConfigured


def postgres_database(environment):
    keys = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_TEST_NAME")
    missing = [key for key in keys if not environment.get(key, "").strip()
               or environment[key].strip() == "REPLACE_ME"]
    if missing:
        raise ImproperlyConfigured("Required PostgreSQL configuration: " + ", ".join(missing))
    try:
        port = int(environment["DB_PORT"])
        timeout = int(environment.get("DB_CONNECT_TIMEOUT", "5"))
    except ValueError:
        raise ImproperlyConfigured("DB_PORT and DB_CONNECT_TIMEOUT must be integers.") from None
    if not 1 <= port <= 65535 or not 1 <= timeout <= 30:
        raise ImproperlyConfigured("DB_PORT must be 1–65535; DB_CONNECT_TIMEOUT must be 1–30 seconds.")
    name, test_name = environment["DB_NAME"].strip(), environment["DB_TEST_NAME"].strip()
    if not re.fullmatch(r"test_[A-Za-z0-9_]+", test_name) or test_name == name or len(test_name) > 63:
        raise ImproperlyConfigured("DB_TEST_NAME must be a distinct test_ name of at most 63 ASCII characters.")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name, "USER": environment["DB_USER"].strip(),
        "PASSWORD": environment["DB_PASSWORD"],
        "HOST": environment["DB_HOST"].strip(), "PORT": str(port),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": timeout, "options": "-c statement_timeout=5000"},
        "TEST": {"NAME": test_name},
    }
