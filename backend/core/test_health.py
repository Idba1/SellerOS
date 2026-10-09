from unittest.mock import MagicMock, patch

from django.db import OperationalError
from django.test import SimpleTestCase
from django.urls import reverse


class ReadinessTests(SimpleTestCase):
    def probe(self, result=(1,), error=None):
        dependency = MagicMock()
        dependency.databases = {"default": {"ENGINE": "django.db.backends.postgresql"}}
        cursor = dependency.__getitem__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = result
        cursor.execute.side_effect = error
        return dependency, cursor

    def test_unconfigured_database_is_not_ready(self):
        with patch("core.health.connections") as dependency:
            dependency.databases = {}
            response = self.client.get(reverse("readiness"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {
            "status": "not_ready", "checks": {"app": "ok", "database": "not_configured"},
        })
        self.assertIn("no-store", response["Cache-Control"])

    def test_ready_requires_successful_query(self):
        dependency, cursor = self.probe()
        with patch("core.health.connections", dependency):
            response = self.client.get(reverse("readiness"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "ready", "checks": {"app": "ok", "database": "ok"},
        })
        cursor.execute.assert_called_once_with("SELECT 1")

    def test_failures_do_not_leak_and_liveness_survives(self):
        for error in (OperationalError("private credentials and host"), RuntimeError("internal trace")):
            dependency, _ = self.probe(error=error)
            with self.subTest(error=type(error).__name__), patch("core.health.connections", dependency):
                response = self.client.get(reverse("readiness"))
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {
                    "status": "not_ready", "checks": {"app": "ok", "database": "unavailable"},
                })
                self.assertEqual(self.client.get(reverse("health")).json(), {"status": "ok"})

    def test_unexpected_query_result_and_methods(self):
        dependency, _ = self.probe(result=None)
        with patch("core.health.connections", dependency):
            self.assertEqual(self.client.get(reverse("readiness")).status_code, 503)
        with patch("core.health.connections", dependency):
            self.assertEqual(self.client.head(reverse("readiness")).status_code, 503)
        self.assertEqual(self.client.post(reverse("readiness")).status_code, 405)
