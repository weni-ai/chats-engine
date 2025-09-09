from unittest.mock import Mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory

from chats.apps.api.v1.external.throttling import (
    ExternalMinuteRateThrottle,
    ExternalSecondRateThrottle,
)


class ExternalThrottlingTest(TestCase):
    """Tests for throttling for external endpoints - always authenticated"""

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
        """Tests that the throttle blocks after reaching the limit"""
        api_settings.reload()
        throttle = ExternalSecondRateThrottle()
        self.assertEqual(throttle.rate, "5/second")

        request = self.factory.get("/")
        request.user = "test@example.com"
        view = Mock()
        key = throttle.get_cache_key(request, view)
        self.assertTrue(key.startswith("throttle_external_second_"))

        for i in range(5):
            result = throttle.allow_request(request, view)
            self.assertTrue(result, f"Request {i+1} should pass")
        hist = cache.get(key, [])
        self.assertEqual(len(hist), 5, f"History should have 5 events, has {len(hist)}")

        result = throttle.allow_request(request, view)
        self.assertFalse(result, "6th request should be blocked")

    def test_different_users_different_limits(self):
        """Tests that different users have independent limits"""
        throttle = ExternalMinuteRateThrottle()
        view = Mock()

        request1 = self.factory.get("/")
        request1.user = "user1@example.com"

        request2 = self.factory.get("/")
        request2.user = "user2@example.com"

        for i in range(10):
            throttle.allow_request(request1, view)

        result = throttle.allow_request(request2, view)
        self.assertTrue(result, "User 2 should have independent limit")

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "external_second": "1/second",
            }
        },
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        },
    )
    def test_internal_user_bypasses_throttling(self):
        """Internal user should not be throttled"""
        api_settings.reload()
        throttle = ExternalSecondRateThrottle()
        self.assertEqual(throttle.rate, "1/second")

        class InternalUser:
            pk = 123

            def has_perm(self, perm):
                return perm == "accounts.can_communicate_internally"

        request = self.factory.get("/")
        request.user = InternalUser()
        view = Mock()

        # Even with 1/second limit, all should pass due to bypass
        for _ in range(10):
            self.assertTrue(throttle.allow_request(request, view))

        # Since there was bypass, there should be no history saved in cache
        key = throttle.get_cache_key(request, view)
        hist = cache.get(key)
        self.assertIsNone(hist, "History should not exist for user with bypass")

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "external_second": "2/second",
            }
        },
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        },
    )
    def test_regular_user_without_internal_perm_is_throttled(self):
        """Regular user (object) without internal permission continues to be throttled"""
        api_settings.reload()
        throttle = ExternalSecondRateThrottle()
        self.assertEqual(throttle.rate, "2/second")

        class RegularUser:
            pk = 456

            def has_perm(self, perm):
                return False

        request = self.factory.get("/")
        request.user = RegularUser()
        view = Mock()

        self.assertTrue(throttle.allow_request(request, view))
        self.assertTrue(throttle.allow_request(request, view))
        self.assertFalse(
            throttle.allow_request(request, view), "Third request should be blocked"
        )
