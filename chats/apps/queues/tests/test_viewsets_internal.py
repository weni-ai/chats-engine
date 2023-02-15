from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector


class QueueAuthTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_sector.json']

    def setUp(self):
        self.project = Project.objects.get(pk='34a93b52-231e-11ed-861d-0242ac120002')
        self.sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        self.queue = Queue.objects.get(pk='f2519480-7e58-4fc4-9894-9ab1769e29cf')
        self.manager_user = User.objects.get(pk=8)
        self.manager_token =  Token.objects.get(user=self.manager_user)
        self.agent_user = User.objects.get(pk=6)
        self.agent_token =  Token.objects.get(user=self.agent_user)
        self.admin_user = User.objects.get(pk=1)
        self.admin_token =  Token.objects.get(user=self.admin_user)
        self.authorization_queue_token = QueueAuthorization.objects.get(permission='e416fd45-2896-43a5-bd7a-5067f03c77fa')

        self.queue_1 = Queue.objects.create(
            name="suport queue", sector=self.sector
        )

    def list_internal_queue_request(self, token):
        url = reverse("queue_auth-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"queue": self.queue.pk})
        return response

    def test_list_auth_queue_with_admin_token(self):
        """
        Verify if the list endpoint for auth queue its returning the correct object using admin token.
        """
        response = self.list_internal_queue_request(self.admin_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 1)

    def retrieve_auth_queue_request(self, token):
        """
        Verify if the retrieve endpoint for auth queue its returning the correct object.
        """
        url = reverse("queue_auth-detail", args=[self.authorization_queue_token.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector})
        return response

    def test_retrieve_auth_queue_with_admin_token(self):
        """
        Verify if the retrieve endpoint for auth queue its returning the correct object using admin token.
        """
        response = self.retrieve_auth_queue_request(self.admin_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.authorization_queue_token.pk))

    def test_create_auth_queue_with_admin_token(self):
        """
        Verify if the create endpoint for auth queue its working correctly.
        """
        url = reverse("queue_auth-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        data = {"role": "1", "queue": str(self.queue_1.pk), "permission": 'e416fd45-2896-43a5-bd7a-5067f03c77fa'}
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_auth_queue_with_manager_token(self):
        """
        Verify if the update endpoint for auth queue its working correctly.
        """
        url = reverse("queue_auth-detail", args=[self.authorization_queue_token.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        data = {
            "queue": str(self.queue_1.pk),
            "permission": '101cb6b3-9de3-4b04-8e60-8a7f42ccba54'
        }
        response = client.patch(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_auth_queue_with_manager_token(self):
        """
        Verify if the delete endpoint for auth queue its working correctly.
        """
        url = reverse("queue_auth-detail", args=[self.authorization_queue_token.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
