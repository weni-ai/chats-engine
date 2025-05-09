from django.test import TestCase
import hmac
import json

from django.conf import settings
from django.http import HttpRequest
from rest_framework.exceptions import AuthenticationFailed

from chats.apps.api.v1.internal.ai_features.auth.classes import (
    AIFeaturesAuthentication,
    verify_signature,
)


class VerifySignatureTests(TestCase):
    def setUp(self):
        self.secret = "test_secret"
        self.body = json.dumps({"message": "test message"})

        # Generate a valid signature for testing
        self.valid_signature = hmac.new(
            bytes(self.secret, "utf-8"), bytes(self.body, "utf-8"), "sha256"
        ).hexdigest()

    def test_verify_signature_valid(self):
        """Test that a valid signature is verified correctly"""
        result = verify_signature(self.secret, self.valid_signature, self.body)
        self.assertTrue(result)

    def test_verify_signature_invalid(self):
        """Test that an invalid signature is rejected"""
        result = verify_signature(self.secret, "invalid_signature", self.body)
        self.assertFalse(result)

    def test_verify_signature_wrong_secret(self):
        """Test that using wrong secret fails verification"""
        wrong_secret = "wrong_secret"
        result = verify_signature(wrong_secret, self.valid_signature, self.body)
        self.assertFalse(result)

    def test_verify_signature_different_body(self):
        """Test that different body content fails verification"""
        different_body = json.dumps({"message": "different message"})
        result = verify_signature(self.secret, self.valid_signature, different_body)
        self.assertFalse(result)


class AIFeaturesAuthenticationTests(TestCase):
    def setUp(self):
        self.secret = "test_secret"
        self.signature_header_name = "X-Weni-Signature"
        self.body = json.dumps({"message": "test message"})
        self.valid_signature = hmac.new(
            bytes(self.secret, "utf-8"), bytes(self.body, "utf-8"), "sha256"
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
        request.headers = {self.signature_header_name: self.valid_signature}

        auth = AIFeaturesAuthentication()
        auth.authenticate(request)

    def test_authenticate_invalid_signature(self):
        """Test authentication fails with invalid signature"""
        # Create a mock request with invalid signature
        request = HttpRequest()
        request._body = self.body
        request.method = "POST"
        request.headers = {self.signature_header_name: "invalid_signature"}

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
        request.headers = {}

        auth = AIFeaturesAuthentication()

        with self.assertRaises(AuthenticationFailed) as context:
            auth.authenticate(request)

        self.assertEqual(str(context.exception), "No signature found")
