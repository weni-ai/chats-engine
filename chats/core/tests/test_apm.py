import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from chats.core.middleware import ElasticAPMTraceResponseHeaderMiddleware

APM_MIDDLEWARE = "elasticapm.contrib.django.middleware.TracingMiddleware"
APM_RESPONSE_HEADER_MIDDLEWARE = (
    "chats.core.middleware.ElasticAPMTraceResponseHeaderMiddleware"
)
APM_APP = "elasticapm.contrib.django"
TRACE_RESPONSE_HEADERS = ("traceparent", "tracestate", "elastic-apm-traceparent")
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ApmConfigurationTestCase(TestCase):
    def test_apm_disabled_by_default(self):
        self.assertFalse(settings.USE_APM)

    def test_tracing_middleware_not_registered_when_apm_disabled(self):
        self.assertNotIn(APM_MIDDLEWARE, settings.MIDDLEWARE)

    def test_trace_response_header_middleware_not_registered_when_apm_disabled(self):
        self.assertNotIn(APM_RESPONSE_HEADER_MIDDLEWARE, settings.MIDDLEWARE)

    def test_elasticapm_app_not_registered_when_apm_disabled(self):
        self.assertNotIn(APM_APP, settings.INSTALLED_APPS)

    def test_trace_headers_are_exposed_through_cors(self):
        """
        Browsers can only read response headers that are listed in
        Access-Control-Expose-Headers. Without this exposure, the Elastic APM
        trace identifiers are stripped from XHR/fetch responses in DevTools.
        """
        exposed = {header.lower() for header in settings.CORS_EXPOSE_HEADERS}
        for header in TRACE_RESPONSE_HEADERS:
            self.assertIn(header, exposed)

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
assert settings.MIDDLEWARE[1] == "chats.core.middleware.ElasticAPMTraceResponseHeaderMiddleware"
assert "elasticapm.contrib.django" in settings.INSTALLED_APPS
assert settings.ELASTIC_APM["SERVICE_NAME"] == "chats-production"
assert settings.ELASTIC_APM["SERVER_URL"] == "http://localhost:8200"
assert settings.ELASTIC_APM["USE_ELASTIC_TRACEPARENT_HEADER"] is True

exposed = {header.lower() for header in settings.CORS_EXPOSE_HEADERS}
for header in ("traceparent", "tracestate", "elastic-apm-traceparent"):
    assert header in exposed, header
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


class ElasticAPMTraceResponseHeaderMiddlewareTests(TestCase):
    """
    The middleware must copy the APM trace identifiers onto every response so
    the values are visible in DevTools/Network and consumable by frontend
    instrumentation. The upstream agent does not do this on its own.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def _run(self, transaction):
        request = self.factory.get("/anything")

        def get_response(_request):
            return HttpResponse("ok")

        middleware = ElasticAPMTraceResponseHeaderMiddleware(get_response)

        with mock.patch(
            "elasticapm.get_transaction", return_value=transaction
        ):
            return middleware(request)

    def test_writes_w3c_and_legacy_headers_when_transaction_active(self):
        trace_parent = mock.Mock()
        trace_parent.to_string.return_value = (
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        )
        trace_parent.tracestate = "vendor=value"
        transaction = mock.Mock(trace_parent=trace_parent)

        response = self._run(transaction)

        self.assertEqual(
            response["traceparent"],
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
        )
        self.assertEqual(
            response["elastic-apm-traceparent"],
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
        )
        self.assertEqual(response["tracestate"], "vendor=value")

    def test_skips_tracestate_when_absent(self):
        trace_parent = mock.Mock()
        trace_parent.to_string.return_value = (
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        )
        trace_parent.tracestate = None
        transaction = mock.Mock(trace_parent=trace_parent)

        response = self._run(transaction)

        self.assertIn("traceparent", response)
        self.assertIn("elastic-apm-traceparent", response)
        self.assertNotIn("tracestate", response)

    def test_noop_when_no_active_transaction(self):
        response = self._run(transaction=None)

        for header in TRACE_RESPONSE_HEADERS:
            self.assertNotIn(header, response)

    def test_noop_when_transaction_has_no_trace_parent(self):
        response = self._run(transaction=mock.Mock(trace_parent=None))

        for header in TRACE_RESPONSE_HEADERS:
            self.assertNotIn(header, response)

    def test_noop_when_elasticapm_not_installed(self):
        request = self.factory.get("/anything")

        def get_response(_request):
            return HttpResponse("ok")

        middleware = ElasticAPMTraceResponseHeaderMiddleware(get_response)

        with mock.patch.dict(sys.modules, {"elasticapm": None}):
            response = middleware(request)

        for header in TRACE_RESPONSE_HEADERS:
            self.assertNotIn(header, response)

    def test_swallow_errors_reading_transaction(self):
        request = self.factory.get("/anything")

        def get_response(_request):
            return HttpResponse("ok")

        middleware = ElasticAPMTraceResponseHeaderMiddleware(get_response)

        with mock.patch(
            "elasticapm.get_transaction", side_effect=RuntimeError("boom")
        ):
            response = middleware(request)

        self.assertEqual(response.status_code, 200)
        for header in TRACE_RESPONSE_HEADERS:
            self.assertNotIn(header, response)
