"""Small local env-file reader: no execution, expansion, or secret diagnostics."""
import os
import re

from django.core.exceptions import ImproperlyConfigured


def load_local_env(path, environ=None):
    target = os.environ if environ is None else environ
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return
    except (OSError, UnicodeError):
        raise ImproperlyConfigured("Cannot read backend/.env as UTF-8.") from None
    values = {}
    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ImproperlyConfigured(f"Invalid backend/.env syntax at line {number}.")
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ImproperlyConfigured(f"Invalid backend/.env quoting at line {number}.")
            value = value[1:-1]
        values[key] = value
    # Parse completely before changing environment; explicit process values win.
    for key, value in values.items():
        target.setdefault(key, value)
