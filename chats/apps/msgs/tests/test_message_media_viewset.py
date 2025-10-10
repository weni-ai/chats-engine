from rest_framework.test import APITestCase
from rest_framework.response import Response
from django.urls import reverse
from rest_framework import status

from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.accounts.models import User
from chats.apps.projects.tests.decorators import with_project_permission
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message, MessageMedia


class BaseTestMessageMediaViewset(APITestCase):
    def list_message_media(self, query_params: dict = None) -> Response:
        url = reverse("message-media-list")
        response = self.client.get(url, query_params)

        return response


class TestMessageMediaViewSetAsAnonymousUser(BaseTestMessageMediaViewset):
    def test_cannot_list_message_media_as_unauthenticated_user(self):
        response = self.list_message_media()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestMessageMediaViewSetAsAuthenticatedUser(BaseTestMessageMediaViewset):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
        )
        self.project = Project.objects.create(name="Test Project")

        self.client.force_authenticate(self.user)

    def _create_room(self):
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.contact = Contact.objects.create(
            name="Test Contact", external_id="test-external-id"
        )
        self.room = Room.objects.create(
            queue=self.queue, user=self.user, contact=self.contact
        )

    @with_project_permission()
    def test_list_message_media(self):
        self._create_room()

        message = Message.objects.create(room=self.room)
        MessageMedia.objects.create(message=message, content_type="image")

        response = self.list_message_media(
            query_params={"room": self.room.uuid, "contact": self.contact.uuid}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
