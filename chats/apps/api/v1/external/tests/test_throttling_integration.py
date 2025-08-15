from unittest.mock import Mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.request import Request
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory

from chats.apps.api.v1.external.throttling import (
    ExternalMinuteRateThrottle,
    ExternalSecondRateThrottle,
)


class ExternalThrottlingTest(TestCase):
    """Testes de throttling para endpoints externos - sempre autenticados"""

    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()

    def tearDown(self):
        cache.clear()

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "external_second": "5/second",
            }
        },
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        },
    )
    def test_throttle_blocks_after_limit(self):
        """Testa que o throttle bloqueia após atingir limite"""
        api_settings.reload()
        throttle = ExternalSecondRateThrottle()
        self.assertEqual(throttle.rate, "5/second")

        request = self.factory.get("/")
        request.user = "test@example.com"
        request = Request(request)
        view = Mock()
        key = throttle.get_cache_key(request, view)
        self.assertTrue(key.startswith("throttle_external_second_"))

        for i in range(5):
            result = throttle.allow_request(request, view)
            self.assertTrue(result, f"Requisição {i+1} deveria passar")
        hist = cache.get(key, [])
        self.assertEqual(
            len(hist), 5, f"Histórico deveria ter 5 eventos, tem {len(hist)}"
        )

        result = throttle.allow_request(request, view)
        self.assertFalse(result, "6ª requisição deveria ser bloqueada")

    def test_different_users_different_limits(self):
        """Testa que usuários diferentes têm limites independentes"""
        throttle = ExternalMinuteRateThrottle()
        view = Mock()

        request1 = self.factory.get("/")
        request1.user = "user1@example.com"
        request1 = Request(request1)

        request2 = self.factory.get("/")
        request2.user = "user2@example.com"
        request2 = Request(request2)

        for i in range(10):
            throttle.allow_request(request1, view)

        result = throttle.allow_request(request2, view)
        self.assertTrue(result, "Usuário 2 deveria ter limite independente")
