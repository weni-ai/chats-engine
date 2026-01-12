import uuid
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.response import Response

from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector
from chats.apps.contacts.models import Contact
from chats.apps.rooms.models import Room


class BaseTestRoomsContactsInternalViewSet(APITestCase):
    def list(self, data: dict) -> Response:
        url = reverse("contact_internal-list")

        return self.client.get(url, data=data)


class TestRoomsContactsInternalViewSetAsAnonymousUser(
    BaseTestRoomsContactsInternalViewSet
):
    def test_list_contacts_as_anonymous_user(self):
        response = self.list(data={"project": str(uuid.uuid4())})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestRoomsContactsInternalViewSetAsAuthenticatedUser(
    BaseTestRoomsContactsInternalViewSet
):
    def setUp(self):
        self.user = User.objects.create(email="internal.project@vtex.com")
        self.project = Project.objects.create(name="Test Project")

        self.client.force_authenticate(self.user)

    def test_list_contacts_without_permission(self):
        response = self.list(data={"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_list_contact_with_permission_without_project(self):
        response = self.list(data={})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["project"][0].code, "required")

    @with_internal_auth
    def test_list_contact_with_permission_with_project(self):
        contacts = []

        for project in (self.project, Project.objects.create(name="Other Project")):
            sector = Sector.objects.create(
                name="Test Sector",
                project=project,
                work_start="09:00",
                work_end="18:00",
                rooms_limit=10,
            )
            queue = Queue.objects.create(name="Test Queue", sector=sector)
            contact = Contact.objects.create(
                name="Test Contact", email="test@contact.com"
            )
            contacts.append(contact)
            Room.objects.create(contact=contact, queue=queue)

        response = self.list(data={"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], contacts[0].name)
