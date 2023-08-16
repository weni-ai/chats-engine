from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.core.tests.test_base import BaseAPIChatsTestCase


class TestContactsViewsets(BaseAPIChatsTestCase):
    def _list_request(self, token, data):
        url = reverse("contact-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = client.get(url, format="json", data=data)
        results = response.json().get("results")
        return response, results

    def test_admin_list_within_its_project(self):
        payload = {"project": str(self.project.uuid)}
        self.deactivate_rooms()
        response = self._list_request(token=self.admin_token, data=payload)[0]
        # print("response", response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), self.count_project_1_contact)

    def test_manager_list_within_its_sectors(self):
        payload = {"project": str(self.project.uuid)}
        self.deactivate_rooms()
        response = self._list_request(token=self.manager_token, data=payload)[0]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 3)

    def test_agent_list_within_its_rooms(self):
        payload = {"project": str(self.project.uuid)}
        self.deactivate_rooms()
        response, results = self._list_request(token=self.agent_token, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_retrieve_contact_ok(self):
        """
        Ensure we can retrieve a contact
        """
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        self.contact.rooms.update(is_active=False, ended_at=timezone.now())
        url = (
            reverse("contact-detail", kwargs={"pk": str(self.contact.pk)})
            + f"?project={str(self.project.uuid)}"
        )
        response = client.get(
            url,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_contact_no_closed_rooms(self):
        """
        Ensure we can retrieve a contact
        """
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        url = (
            reverse("contact-detail", kwargs={"pk": str(self.contact.pk)})
            + f"?project={str(self.project.uuid)}"
        )
        response = self.client.get(
            url,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_contact_unauthorized(self):
        """
        Ensure we can retrieve a contact
        """
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.agent_token.key)
        url = (
            reverse("contact-detail", kwargs={"pk": str(self.contact_2.pk)})
            + f"?project={str(self.project.uuid)}"
        )
        response = client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_handling_not_allowed_http_methods(self):
        url = reverse("contact-detail", kwargs={"pk": 1})
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        post = client.post(url, format="json")
        put = client.put(url, format="json")
        delete = client.delete(url, format="json")
        actions = [post, put, delete]

        for action in actions:
            self.assertEqual(action.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestContactSerializer(APITestCase):
    def test_correct_contact_serialization(self):
        """
        Ensure we can serialize a contact when passed correct data
        """
        data = {"email": "test@email.com", "name": "Test Contact"}
        serializer = ContactSerializer(data=data)
        is_valid = serializer.is_valid()
        contact = serializer.validated_data

        self.assertTrue(is_valid)
        self.assertEqual(contact["email"], data["email"])
        self.assertEqual(contact["name"], data["name"])

    def test_detect_invalid_data(self):
        """
        Ensure we can detect invalid data on serialize
        """
        data = {"name": None, "email": None}

        serializer = ContactSerializer(data=data)
        self.assertFalse(serializer.is_valid())
