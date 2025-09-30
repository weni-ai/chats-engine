from datetime import timedelta
import uuid
import jwt

from django.utils import timezone
from django.test import TestCase
from django.http import HttpRequest
from django.test import override_settings
from rest_framework.views import APIView
from rest_framework.test import APITestCase, APIClient
from rest_framework.response import Response
from rest_framework import status

from chats.apps.api.authentication.classes import JWTAuthentication
from chats.apps.api.authentication.token import JWTTokenGenerator


from chats.apps.api.authentication.permissions import JWTRequiredPermission


class JWTAuthenticationTests(TestCase):
    def setUp(self):
        self.token_generator = JWTTokenGenerator()
        self.valid_token = self.token_generator.generate_token(
            {"user_id": 1, "username": "testuser"}
        )

    def test_authenticate(self):
        authentication = JWTAuthentication()
        request = HttpRequest()
        request.META["HTTP_AUTHORIZATION"] = self.valid_token
        result = authentication.authenticate(request)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertIsNone(result[0])
        self.assertIsNotNone(result[1])

    def test_authenticate_credentials(self):
        authentication = JWTAuthentication()
        result = authentication.authenticate_credentials(self.valid_token)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertIsNone(result[0])
        self.assertIsNotNone(result[1])


class MockView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [JWTRequiredPermission]

    def get(self, request):
        """Test endpoint that returns the authenticated data from the token."""

        return Response(
            {
                "authenticated": request.auth is not None,
                "token_data": request.auth if request.auth else None,
            }
        )


@override_settings(ROOT_URLCONF="chats.apps.api.authentication.tests.test_urls")
class MockViewAPITestCase(APITestCase):
    """Test cases for MockView using JWTAuthentication."""

    def setUp(self):
        self.client = APIClient()
        self.token_generator = JWTTokenGenerator()
        self.test_payload = {
            "room": str(uuid.uuid4()),
        }
        self.valid_token = self.token_generator.generate_token(self.test_payload)

    def test_authenticated_request_with_valid_token(self):
        """Test that a request with a valid JWT token is authenticated and token data is available."""
        response = self.client.get("/mock/", HTTP_AUTHORIZATION=self.valid_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["authenticated"])
        self.assertIsNotNone(response.data["token_data"])

        # Verify that the token data contains the original payload
        token_data = response.data["token_data"]
        self.assertEqual(token_data["room"], self.test_payload["room"])

        # Verify JWT standard claims are present
        self.assertIn("iat", token_data)
        self.assertIn("exp", token_data)
        self.assertIn("nbf", token_data)

    def test_unauthenticated_request_without_token(self):
        """Test that a request without a token is not authenticated."""
        response = self.client.get("/mock/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_request_with_invalid_token(self):
        """Test that a request with an invalid token is not authenticated."""
        invalid_token = "invalid.jwt.token"
        response = self.client.get("/mock/", HTTP_AUTHORIZATION=invalid_token)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_request_with_malformed_token(self):
        """Test that a request with a malformed token is not authenticated."""
        malformed_token = "Bearer invalid.jwt.token"
        response = self.client.get("/mock/", HTTP_AUTHORIZATION=malformed_token)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_request_with_expired_token(self):
        """Test that a request with an expired token is not authenticated."""
        expired_payload = {
            **self.test_payload,
            "iat": int((timezone.now() - timedelta(hours=25)).timestamp()),
            "exp": int((timezone.now() - timedelta(hours=1)).timestamp()),
            "nbf": int((timezone.now() - timedelta(hours=25)).timestamp()),
        }

        expired_token = jwt.encode(
            expired_payload,
            self.token_generator.secret_key,
            algorithm=self.token_generator.algorithm,
        )

        response = self.client.get("/mock/", HTTP_AUTHORIZATION=expired_token)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_data_structure(self):
        """Test that the token data structure is correct and complete."""
        response = self.client.get("/mock/", HTTP_AUTHORIZATION=self.valid_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token_data = response.data["token_data"]

        for key, value in self.test_payload.items():
            self.assertEqual(token_data[key], value)

        self.assertIsInstance(token_data["iat"], int)
        self.assertIsInstance(token_data["exp"], int)
        self.assertIsInstance(token_data["nbf"], int)

        current_time = int(timezone.now().timestamp())
        self.assertGreater(token_data["exp"], current_time)
