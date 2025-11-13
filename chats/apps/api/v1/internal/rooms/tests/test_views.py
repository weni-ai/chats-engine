from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.accounts.tests.decorators import with_internal_auth


class BaseTestInternalProtocolRoomsViewSet(APITestCase):
    def list_protocols(self, filters: dict = {}) -> Response:
        url = f"/v1/internal/rooms/protocols/"
        return self.client.get(url, filters)


class TestInternalProtocolRoomsViewSetAsAnonymousUser(
    BaseTestInternalProtocolRoomsViewSet
):
    def test_list_protocols_without_authentication(self):
        response = self.list_protocols()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestInternalProtocolRoomsViewSetAsAuthenticatedUser(
    BaseTestInternalProtocolRoomsViewSet
):
    def setUp(self):
        self.user = User.objects.create_user(email="internal@vtex.com")
        self.project = Project.objects.create(name="Test Project")

        self.client.force_authenticate(self.user)

    def test_list_protocols_without_permission(self):
        response = self.list_protocols()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_list_protocols_with_permission(self):
        response = self.list_protocols({"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
