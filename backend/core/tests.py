import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import reverse


class HealthTests(SimpleTestCase):
    def test_public_health_returns_only_liveness(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_head_and_rejected_write(self):
        self.assertEqual(self.client.head(reverse("health")).status_code, 200)
        response = self.client.post(reverse("health"))
        self.assertEqual(response.status_code, 405)

    def test_startup_requires_environment_secret(self):
        environment = os.environ.copy()
        environment.pop("DJANGO_SECRET_KEY", None)
        result = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY must be supplied", result.stderr)
