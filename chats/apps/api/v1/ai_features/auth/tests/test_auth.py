from django.test import TestCase
import hmac
import json

from chats.apps.api.v1.ai_features.auth.classes import verify_signature


class VerifySignatureTests(TestCase):
    def setUp(self):
        self.secret = "test_secret"
        self.signature_header_name = "X-Weni-Signature"
        self.body = json.dumps({"message": "test message"})

        # Generate a valid signature for testing
        self.valid_signature = hmac.new(
            bytes(self.secret, "utf-8"), bytes(self.body, "utf-8"), "sha256"
        ).hexdigest()

        self.headers = {self.signature_header_name: f"v1={self.valid_signature}"}

    def test_verify_signature_valid(self):
        """Test that a valid signature is verified correctly"""
        result = verify_signature(
            self.signature_header_name, self.secret, self.headers, self.body
        )
        self.assertTrue(result)

    def test_verify_signature_invalid(self):
        """Test that an invalid signature is rejected"""
        headers = {self.signature_header_name: "v1=invalid_signature"}
        result = verify_signature(
            self.signature_header_name, self.secret, headers, self.body
        )
        self.assertFalse(result)

    def test_verify_signature_missing_header(self):
        """Test that missing signature header returns False"""
        headers = {}
        result = verify_signature(
            self.signature_header_name, self.secret, headers, self.body
        )
        self.assertFalse(result)

    def test_verify_signature_wrong_secret(self):
        """Test that using wrong secret fails verification"""
        wrong_secret = "wrong_secret"
        result = verify_signature(
            self.signature_header_name, wrong_secret, self.headers, self.body
        )
        self.assertFalse(result)

    def test_verify_signature_different_body(self):
        """Test that different body content fails verification"""
        different_body = json.dumps({"message": "different message"})
        result = verify_signature(
            self.signature_header_name, self.secret, self.headers, different_body
        )
        self.assertFalse(result)
