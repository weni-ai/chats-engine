from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response


from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.contacts.models import Contact
from chats.apps.accounts.models import User
from chats.apps.projects.tests.decorators import with_project_permission
from chats.apps.msgs.models import Message, MessageMedia


class BaseTestMessageMediaViewSet(APITestCase):
    def list_media(self, params: dict) -> Response:
        url = reverse("media-list")

        return self.client.get(url, params)


class TestMessageMediaViewSetAsAnonymousUser(BaseTestMessageMediaViewSet):
    def test_list_media_as_anonymous_user(self):
        response = self.list_media({})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestMessageMediaViewSetAsAuthenticatedUser(BaseTestMessageMediaViewSet):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            work_start="09:00",
            work_end="18:00",
            rooms_limit=10,
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact", email="test@test.com"),
            is_active=True,
            queue=self.queue,
        )
        self.user = User.objects.create_user(
            email="test@test.com", password="testpass123"
        )

        self.client.force_authenticate(user=self.user)

    def test_list_media_without_permission(self):
        response = self.list_media({"room": self.room.uuid})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_when_user_is_room_user(self):
        self.room.user = self.user
        self.room.save(update_fields=["user"])

        response = self.list_media({"room": self.room.uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @with_project_permission()
    def test_list_when_user_with_without_room_and_project_query_param(
        self,
    ):
        response = self.list_media({})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"][0].code, "required")

    @with_project_permission()
    def test_list_when_user_with_project_permission_and_project_query_param(self):
        response = self.list_media({"project": self.project.uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @with_project_permission()
    def test_list_when_user_with_project_permission_and_room_query_param(self):
        message = Message.objects.create(room=self.room, user=self.user)
        MessageMedia.objects.create(message=message)
        response = self.list_media({"room": self.room.uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @with_project_permission()
    def test_list_when_user_filtering_by_room_and_contact(self):
        message = Message.objects.create(room=self.room, user=self.user)
        MessageMedia.objects.create(message=message)
        response = self.list_media(
            {"room": self.room.uuid, "contact": self.room.contact.uuid}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["message"], message.uuid)
