import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.test import TestCase

APM_MIDDLEWARE = "elasticapm.contrib.django.middleware.TracingMiddleware"
APM_APP = "elasticapm.contrib.django"
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ApmConfigurationTestCase(TestCase):
    def test_apm_disabled_by_default(self):
        self.assertFalse(settings.USE_APM)

    def test_tracing_middleware_not_registered_when_apm_disabled(self):
        self.assertNotIn(APM_MIDDLEWARE, settings.MIDDLEWARE)

    def test_elasticapm_app_not_registered_when_apm_disabled(self):
        self.assertNotIn(APM_APP, settings.INSTALLED_APPS)

    def _build_subprocess_env(self, **overrides):
        env = os.environ.copy()
        env.update(
            {
                "DJANGO_SETTINGS_MODULE": "chats.settings",
                "SECRET_KEY": settings.SECRET_KEY,
                "PROMETHEUS_AUTH_TOKEN": settings.PROMETHEUS_AUTH_TOKEN,
            }
        )
        if "DATABASE_URL" not in env:
            database = settings.DATABASES["default"]
            if database["ENGINE"] == "django.db.backends.sqlite3":
                env["DATABASE_URL"] = f"sqlite:///{database['NAME']}"
            else:
                env["DATABASE_URL"] = (
                    f"postgres://{database['USER']}:{database['PASSWORD']}"
                    f"@{database['HOST']}:{database['PORT']}/{database['NAME']}"
                )
        env.update(overrides)
        return env

    def test_settings_registers_apm_when_enabled(self):
        env = self._build_subprocess_env(
            USE_APM="true",
            APM_SECRET_TOKEN="test-token",
            APM_SERVER_URL="http://localhost:8200",
        )
        script = """
import django

django.setup()

from django.conf import settings

assert settings.USE_APM is True
assert settings.MIDDLEWARE[0] == "elasticapm.contrib.django.middleware.TracingMiddleware"
assert "elasticapm.contrib.django" in settings.INSTALLED_APPS
assert settings.ELASTIC_APM["SERVICE_NAME"] == "chats-production"
assert settings.ELASTIC_APM["SERVER_URL"] == "http://localhost:8200"
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr or result.stdout,
        )
