import json
import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class SettingsModeTests(SimpleTestCase):
    def run_mode(self, mode, debug="false", secret=None):
        environment = os.environ.copy()
        environment["DJANGO_SETTINGS_MODULE"] = f"config.settings.{mode}"
        environment["DJANGO_DEBUG"] = debug
        if secret is not None:
            environment["DJANGO_SECRET_KEY"] = secret
        return subprocess.run(
            [sys.executable, "-c",
             "import django,json; django.setup(); "
             "from django.conf import settings; "
             "print(json.dumps({'debug':settings.DEBUG,'hosts':settings.ALLOWED_HOSTS,"
             "'zone':settings.TIME_ZONE,'media':str(settings.MEDIA_ROOT)}))"],
            cwd=Path(__file__).resolve().parents[1],
            env=environment, capture_output=True, text=True, check=False,
        )

    def test_local_validation_and_test_debug_isolation(self):
        local = self.run_mode("local", "true")
        self.assertEqual(local.returncode, 0, local.stderr)
        self.assertTrue(json.loads(local.stdout)["debug"])
        test = self.run_mode("test", "true")
        self.assertEqual(test.returncode, 0, test.stderr)
        self.assertFalse(json.loads(test.stdout)["debug"])
        self.assertIn("testserver", json.loads(test.stdout)["hosts"])
        self.assertNotIn("testserver", json.loads(local.stdout)["hosts"])
        invalid = self.run_mode("local", "maybe")
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("DJANGO_DEBUG must be true or false", invalid.stderr)

    def test_both_modes_require_private_secret(self):
        for mode in ("local", "test"):
            for secret in ("", "REPLACE_ME"):
                with self.subTest(mode=mode, secret=secret):
                    result = self.run_mode(mode, secret=secret)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("DJANGO_SECRET_KEY", result.stderr)
