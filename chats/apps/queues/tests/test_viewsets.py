from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class QueueTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.manager_user = User.objects.get(pk=8)
        self.manager_token = Token.objects.get(user=self.manager_user)
        self.agent_user = User.objects.get(pk=6)
        self.agent_token = Token.objects.get(user=self.agent_user)
        self.admin_user = User.objects.get(pk=1)
        self.admin_token = Token.objects.get(user=self.admin_user)

        self.queue_1 = Queue.objects.create(name="suport queue", sector=self.sector)

    def list_queue_request(self, token):
        """
        Verify if the list endpoint for queue its returning the correct object.
        """
        url = reverse("queue-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector.pk})
        return response

    def test_list_queue_with_admin_token(self):
        """
        Verify if the list endpoint for queue its returning the correct object using admin token.
        """
        response = self.list_queue_request(self.admin_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_list_queue_with_manager_token(self):
        """
        Verify if the list endpoint for queue its returning the correct object using manager token.
        """
        response = self.list_queue_request(self.manager_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_list_queue_with_agent_token(self):
        """
        Verify if the list endpoint for queue its returning the correct object using agent token.
        """
        response = self.list_queue_request(self.agent_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def retrieve_queue_request(self, token):
        """
        Verify if the retrieve endpoint for queue its returning the correct object.
        """
        url = reverse("queue-detail", args=[self.queue_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector.pk})
        return response

    def test_retrieve_queue_with_admin_token(self):
        """
        Verify if the retrieve endpoint for queue its returning the correct object using admin token.
        """
        response = self.retrieve_queue_request(self.admin_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.queue_1.pk))

    def test_create_queue_with_manager_token(self):
        """
        Verify if the create endpoint for queue its working correctly.
        """
        url = reverse("queue-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        data = {
            "name": "queue created by test",
            "sector": str(self.sector.pk),
        }
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_queue_with_manager_token(self):
        """
        Verify if the update endpoint for queue its working correctly.
        """
        url = reverse("queue-detail", args=[self.queue_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        data = {
            "name": "teste 12222223",
        }
        response = client.patch(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_queue_with_manager_token(self):
        """
        Verify if the delete endpoint for queue its working correctly.
        """
        url = reverse("queue-detail", args=[self.queue_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
