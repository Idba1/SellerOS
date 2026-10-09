from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import SimpleTestCase, TestCase

from core.database import postgres_database


class DatabaseConfigurationTests(SimpleTestCase):
    def configuration(self):
        return dict(DB_NAME="development_fixture", DB_USER="fixture", DB_PASSWORD="fixture",
                    DB_HOST="127.0.0.1", DB_PORT="5432", DB_TEST_NAME="test_fixture")

    def test_postgresql_and_bounded_timeouts(self):
        result = postgres_database(self.configuration())
        self.assertEqual(result["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(result["OPTIONS"]["connect_timeout"], 5)
        self.assertEqual(result["TEST"]["NAME"], "test_fixture")

    def test_missing_config_does_not_expose_values(self):
        values = self.configuration()
        values["DB_HOST"] = ""
        with self.assertRaisesMessage(ImproperlyConfigured, "DB_HOST") as error:
            postgres_database(values)
        self.assertNotIn("fixture", str(error.exception))

    def test_invalid_test_name_port_and_timeout(self):
        for key, value in (("DB_TEST_NAME", "development_fixture"), ("DB_TEST_NAME", "unsafe"),
                           ("DB_PORT", "0"), ("DB_CONNECT_TIMEOUT", "31")):
            with self.subTest(key=key), self.assertRaises(ImproperlyConfigured):
                postgres_database({**self.configuration(), key: value})


class PostgreSQLSmokeTests(TestCase):
    def test_test_database_is_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.assertTrue(connection.settings_dict["NAME"].startswith("test_"))
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            self.assertEqual(cursor.fetchone(), (1,))
