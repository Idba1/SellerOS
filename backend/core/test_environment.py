from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from core.environment import load_local_env


class LocalEnvironmentTests(SimpleTestCase):
    def test_quotes_bom_and_process_precedence_without_expansion(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('\ufeff# comment\nA="file=value#literal"\nB=\'$HOME\'\n', encoding="utf-8")
            environment = {"A": "process"}
            load_local_env(path, environment)
            self.assertEqual(environment, {"A": "process", "B": "$HOME"})

    def test_invalid_file_is_atomic_and_diagnostics_hide_values(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("A=value\ninvalid private-content\n", encoding="utf-8")
            environment = {}
            with self.assertRaisesMessage(ImproperlyConfigured, "syntax at line 2") as error:
                load_local_env(path, environment)
            self.assertNotIn("private-content", str(error.exception))
            self.assertEqual(environment, {})

    def test_missing_file_does_not_override_configuration(self):
        with TemporaryDirectory() as directory:
            environment = {"A": "process"}
            load_local_env(Path(directory) / ".env", environment)
            self.assertEqual(environment, {"A": "process"})
