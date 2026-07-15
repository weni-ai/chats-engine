import uuid
from rest_framework.test import APITestCase
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from chats.apps.api.authentication.classes import JWTAuthentication
from chats.apps.api.authentication.permissions import (
    HasInternalAuthenticationPermission,
)
from django.test import override_settings
from django.urls import reverse

from chats.apps.api.authentication.services.jwt_service import JWTService
from chats.apps.api.authentication.tests.test_jwt_service import (
    generate_private_key,
    generate_private_key_pem,
    generate_public_key,
    generate_public_key_pem,
)
from chats.apps.projects.models.models import Project


TEST_PRIVATE_KEY = generate_private_key()
TEST_PRIVATE_KEY_PEM = generate_private_key_pem(TEST_PRIVATE_KEY)

TEST_PUBLIC_KEY = generate_public_key(TEST_PRIVATE_KEY)
TEST_PUBLIC_KEY_PEM = generate_public_key_pem(TEST_PUBLIC_KEY)


class MockJWTAuthenticationView(APIView):
    authentication_classes = [JWTAuthentication]
    # Same as internal VTEX/conversations views: allow when JWT set request.jwt_payload/project_uuid
    permission_classes = [HasInternalAuthenticationPermission]

    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class TestJWTAuthentication(APITestCase):
    def setUp(self):
        self.jwt_service = JWTService()

    @override_settings(ROOT_URLCONF="chats.apps.api.authentication.tests.test_urls")
    @override_settings(JWT_SECRET_KEY=TEST_PRIVATE_KEY_PEM)
    @override_settings(JWT_PUBLIC_KEY=TEST_PUBLIC_KEY_PEM)
    def test_jwt_authentication(self):
        project = Project.objects.create(name="Test Project")
        token = self.jwt_service.generate_jwt_token(project_uuid=project.uuid)
        url = reverse("mock-jwt-authentication-view")
        response = self.client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})

    @override_settings(ROOT_URLCONF="chats.apps.api.authentication.tests.test_urls")
    @override_settings(JWT_SECRET_KEY=TEST_PRIVATE_KEY_PEM)
    @override_settings(JWT_PUBLIC_KEY=TEST_PUBLIC_KEY_PEM)
    def test_jwt_authentication_project_not_found(self):
        token = self.jwt_service.generate_jwt_token(project_uuid=uuid.uuid4())
        url = reverse("mock-jwt-authentication-view")
        response = self.client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data, {"detail": "Project not found"})

    @override_settings(ROOT_URLCONF="chats.apps.api.authentication.tests.test_urls")
    def test_jwt_authentication_missing_header(self):
        url = reverse("mock-jwt-authentication-view")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(ROOT_URLCONF="chats.apps.api.authentication.tests.test_urls")
    def test_jwt_authentication_invalid_header(self):
        url = reverse("mock-jwt-authentication-view")
        response = self.client.get(url, HTTP_AUTHORIZATION="Bearer invalid-token")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
