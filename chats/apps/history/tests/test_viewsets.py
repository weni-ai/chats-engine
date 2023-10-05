from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from chats.core.tests.test_base import BaseAPIChatsTestCase


class TestHistoryRoomViewsets(BaseAPIChatsTestCase):
    def _list_request(self, token, data):
        url = reverse("history_room-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = client.get(url, format="json", data=data)
        results = response.json().get("results")
        return response, results

    def test_admin_list_within_its_project(self):
        payload = {"project": str(self.project.uuid)}
        self.deactivate_rooms()
        response = self._list_request(token=self.admin_token, data=payload)[0]
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
        response, _ = self._list_request(token=self.agent_token, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_basic_list(self):
        payload = {
            "project": str(self.project.uuid),
            "basic": True,
            "contact": self.contact.external_id,
        }
        self.deactivate_rooms()
        response = self._list_request(token=self.admin_token, data=payload)[0]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 1)
        self.assertEqual(len(response.json().get("results")[0]), 2)

    def test_admin_list_with_blocked_contacts(self):
        self.project.add_contact_to_history_blocklist(self.contact_2.external_id)

        payload = {"project": str(self.project.uuid)}
        self.deactivate_rooms()
        response = self._list_request(token=self.admin_token, data=payload)[0]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), self.count_project_1_contact - 1)

    def test_retrieve_room_ok(self):
        """
        Ensure we can retrieve a contact
        """
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        self.contact.rooms.update(is_active=False, ended_at=timezone.now())
        url = (
            reverse("history_room-detail", kwargs={"pk": str(self.room_1.pk)})
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
            reverse("history_room-detail", kwargs={"pk": str(self.room_1.pk)})
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
        self.contact_2.rooms.update(is_active=False, ended_at=timezone.now())
        url = (
            reverse("history_room-detail", kwargs={"pk": str(self.room_2.pk)})
            + f"?project={str(self.project.uuid)}"
        )
        response = client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_handling_not_allowed_http_methods(self):
        url = reverse("history_room-detail", kwargs={"pk": 1})
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        post = client.post(url, format="json")
        put = client.put(url, format="json")
        delete = client.delete(url, format="json")
        actions = [post, put, delete]

        for action in actions:
            self.assertEqual(action.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
