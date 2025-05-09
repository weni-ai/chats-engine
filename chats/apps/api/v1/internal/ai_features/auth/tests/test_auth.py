from django.test import TestCase
import hmac
import json
import time

from django.conf import settings
from django.http import HttpRequest
from rest_framework.exceptions import AuthenticationFailed

from chats.apps.api.v1.internal.ai_features.auth.classes import (
    AIFeaturesAuthentication,
    verify_signature,
    verify_timestamp,
)


class VerifySignatureTests(TestCase):
    def setUp(self):
        self.secret = "test_secret"
        self.body = json.dumps({"message": "test message"})
        self.timestamp = str(int(time.time()))
        self.message = f"{self.body}+{self.timestamp}"

        # Generate a valid signature for testing
        self.valid_signature = hmac.new(
            bytes(self.secret, "utf-8"), bytes(self.message, "utf-8"), "sha256"
        ).hexdigest()

    def test_verify_signature_valid(self):
        """Test that a valid signature is verified correctly"""
        result = verify_signature(self.secret, self.valid_signature, self.message)
        self.assertTrue(result)

    def test_verify_signature_invalid(self):
        """Test that an invalid signature is rejected"""
        result = verify_signature(self.secret, "invalid_signature", self.message)
        self.assertFalse(result)

    def test_verify_signature_wrong_secret(self):
        """Test that using wrong secret fails verification"""
        wrong_secret = "wrong_secret"
        result = verify_signature(wrong_secret, self.valid_signature, self.message)
        self.assertFalse(result)

    def test_verify_signature_different_message(self):
        """Test that different message content fails verification"""
        different_message = (
            f"{json.dumps({'message': 'different message'})}+{self.timestamp}"
        )
        result = verify_signature(self.secret, self.valid_signature, different_message)
        self.assertFalse(result)


class VerifyTimestampTests(TestCase):
    def test_verify_timestamp_valid(self):
        """Test that a valid timestamp is accepted"""
        timestamp = str(int(time.time()))
        verify_timestamp(timestamp)  # Should not raise an exception

    def test_verify_timestamp_too_old(self):
        """Test that an old timestamp is rejected"""
        old_timestamp = str(int(time.time()) - 301)  # 301 seconds old
        with self.assertRaises(AuthenticationFailed) as context:
            verify_timestamp(old_timestamp)
        self.assertEqual(str(context.exception), "Timestamp is too old")

    def test_verify_timestamp_future(self):
        """Test that a future timestamp is rejected"""
        future_timestamp = str(int(time.time()) + 301)  # 301 seconds in future
        with self.assertRaises(AuthenticationFailed) as context:
            verify_timestamp(future_timestamp)
        self.assertEqual(str(context.exception), "Timestamp is too old")


class AIFeaturesAuthenticationTests(TestCase):
    def setUp(self):
        self.secret = "test_secret"
        self.signature_header_name = "X-Weni-Signature"
        self.timestamp_header_name = "X-Timestamp"
        self.body = json.dumps({"message": "test message"})
        self.timestamp = str(int(time.time()))
        self.message = f"{self.body}+{self.timestamp}"
        self.valid_signature = hmac.new(
            bytes(self.secret, "utf-8"), bytes(self.message, "utf-8"), "sha256"
        ).hexdigest()

        # Mock settings
        self.original_secret = settings.AI_FEATURES_PROMPTS_API_SECRET
        settings.AI_FEATURES_PROMPTS_API_SECRET = self.secret

    def tearDown(self):
        # Restore original settings
        settings.AI_FEATURES_PROMPTS_API_SECRET = self.original_secret

    def test_authenticate_valid_signature(self):
        """Test successful authentication with valid signature"""
        # Create a mock request
        request = HttpRequest()
        request._body = self.body
        request.method = "POST"
        request.headers = {
            self.signature_header_name: self.valid_signature,
            self.timestamp_header_name: self.timestamp,
        }

        auth = AIFeaturesAuthentication()
        auth.authenticate(request)

    def test_authenticate_invalid_signature(self):
        """Test authentication fails with invalid signature"""
        # Create a mock request with invalid signature
        request = HttpRequest()
        request._body = self.body
        request.method = "POST"
        request.headers = {
            self.signature_header_name: "invalid_signature",
            self.timestamp_header_name: self.timestamp,
        }

        auth = AIFeaturesAuthentication()

        with self.assertRaises(AuthenticationFailed) as context:
            auth.authenticate(request)

        self.assertEqual(str(context.exception), "Invalid signature")

    def test_authenticate_missing_signature(self):
        """Test authentication fails when signature header is missing"""
        # Create a mock request without signature header
        request = HttpRequest()
        request._body = self.body
        request.method = "POST"
        request.headers = {self.timestamp_header_name: self.timestamp}

        auth = AIFeaturesAuthentication()

        with self.assertRaises(AuthenticationFailed) as context:
            auth.authenticate(request)

        self.assertEqual(str(context.exception), "No signature found")

    def test_authenticate_missing_timestamp(self):
        """Test authentication fails when timestamp header is missing"""
        # Create a mock request without timestamp header
        request = HttpRequest()
        request._body = self.body
        request.method = "POST"
        request.headers = {self.signature_header_name: self.valid_signature}

        auth = AIFeaturesAuthentication()

        with self.assertRaises(AuthenticationFailed) as context:
            auth.authenticate(request)

        self.assertEqual(str(context.exception), "No timestamp found")

    def test_authenticate_invalid_timestamp(self):
        """Test authentication fails with invalid timestamp"""
        # Create a mock request with old timestamp
        old_timestamp = str(int(time.time()) - 301)  # 301 seconds old
        request = HttpRequest()
        request._body = self.body
        request.method = "POST"
        request.headers = {
            self.signature_header_name: self.valid_signature,
            self.timestamp_header_name: old_timestamp,
        }

        auth = AIFeaturesAuthentication()

        with self.assertRaises(AuthenticationFailed) as context:
            auth.authenticate(request)

        self.assertEqual(str(context.exception), "Timestamp is too old")

    def test_authenticate_safe_method(self):
        """Test authentication succeeds for safe methods"""
        # Create a mock request with safe method
        request = HttpRequest()
        request._body = self.body
        request.method = "GET"
        request.headers = {
            self.signature_header_name: self.valid_signature,
            self.timestamp_header_name: self.timestamp,
        }

        auth = AIFeaturesAuthentication()
        auth.authenticate(request)

        request.method = "HEAD"
        auth.authenticate(request)

        request.method = "OPTIONS"
        auth.authenticate(request)

    def test_authenticate_invalid_timestamp_for_safe_method(self):
        """Test authentication fails for safe methods with invalid timestamp"""
        # Create a mock request with old timestamp
        old_timestamp = str(int(time.time()) - 301)  # 301 seconds old
        request = HttpRequest()
        request._body = self.body
        request.method = "GET"
        request.headers = {
            self.signature_header_name: self.valid_signature,
            self.timestamp_header_name: old_timestamp,
        }

        auth = AIFeaturesAuthentication()

        with self.assertRaises(AuthenticationFailed) as context:
            auth.authenticate(request)

        self.assertEqual(str(context.exception), "Timestamp is too old")
