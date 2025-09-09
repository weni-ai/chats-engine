from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class SectorTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.manager_user = User.objects.get(pk=8)
        self.login_token = Token.objects.get(user=self.manager_user)
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.sector_2 = Sector.objects.get(pk="4f88b656-194d-4a83-a166-5d84ba825b8d")
        self.wrong_user = User.objects.get(pk=1)
        self.wrong_login_token = Token.objects.get_or_create(user=self.wrong_user)[0]

    def test_retrieve_sector_with_right_project_token(self):
        """
        Verify if the list endpoint for sector its returning the correct object.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["automatic_message"]["is_active"], False)
        self.assertIsNone(response.data["automatic_message"]["text"])

    def test_retrieve_sector_with_right_project_token_and_automatic_message_active(
        self,
    ):
        """
        Verify if the list endpoint for sector its returning the correct object.
        """
        self.sector.is_automatic_message_active = True
        self.sector.automatic_message_text = "Hello, how can I help you?"
        self.sector.save(
            update_fields=["is_automatic_message_active", "automatic_message_text"]
        )
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["automatic_message"]["is_active"], True)
        self.assertEqual(
            response.data["automatic_message"]["text"], "Hello, how can I help you?"
        )

    def test_get_sector_list_with_right_project_token(self):
        """
        Ensure that the user need to pass a project_id in order to get the sectors related to them
        """
        self.sector_2.is_automatic_message_active = True
        self.sector_2.automatic_message_text = "Hello, how can I help you?"
        self.sector_2.save(
            update_fields=["is_automatic_message_active", "automatic_message_text"]
        )
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url, data={"project": self.project.pk})
        results = response.json().get("results")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(results[0].get("uuid"), str(self.sector.pk))
        self.assertEqual(results[0].get("automatic_message")["is_active"], False)
        self.assertIsNone(results[0].get("automatic_message")["text"])
        self.assertEqual(results[1].get("uuid"), str(self.sector_2.pk))
        self.assertEqual(results[1].get("automatic_message")["is_active"], True)
        self.assertEqual(
            results[1].get("automatic_message")["text"], "Hello, how can I help you?"
        )

    def test_get_sector_list_with_wrong_project_token(self):
        """
        Ensure that an unauthorized user cannot access the sector list of the project
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.wrong_login_token.key)
        response = client.get(url, data={"project": self.project.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_sector_with_right_project_token(self):
        """
        Verify if the Project Permission its returning the correct value from first_access field.
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {
            "name": "Finances",
            "rooms_limit": 3,
            "work_start": "11:00",
            "work_end": "19:30",
            "project": str(self.project.pk),
        }
        response = client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_sector_with_right_project_token(self):
        """
        Verify if the endpoint for update in sector is working with correctly.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.put(url, data={"name": "sector 2 updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.assertEqual("sector 2 updated", sector.name)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active")
    def test_update_sector_automatic_message_when_feature_flag_is_off(
        self, mock_is_feature_active
    ):
        """
        Verify if the endpoint for update in sector is working with correctly.
        """
        mock_is_feature_active.return_value = False
        self.sector.is_automatic_message_active = False
        self.sector.save(update_fields=["is_automatic_message_active"])
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.patch(
            url,
            data={
                "automatic_message": {
                    "is_active": True,
                    "text": "Hello, how can I help you?",
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["is_automatic_message_active"][0].code,
            "automatic_message_feature_flag_is_not_active",
        )

        self.sector.refresh_from_db()
        self.assertFalse(self.sector.is_automatic_message_active)
        self.assertIsNone(self.sector.automatic_message_text)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active")
    def test_update_sector_automatic_message_when_feature_flag_is_on(
        self, mock_is_feature_active
    ):
        """
        Verify if the endpoint for update in sector is working with correctly.
        """
        mock_is_feature_active.return_value = True
        self.sector.is_automatic_message_active = False
        self.sector.save(update_fields=["is_automatic_message_active"])
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        text = "Hello, how can I help you?"
        response = client.patch(
            url,
            data={
                "automatic_message": {
                    "is_active": True,
                    "text": text,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["automatic_message"]["is_active"], True)
        self.assertEqual(response.data["automatic_message"]["text"], text)

        self.sector.refresh_from_db()
        self.assertTrue(self.sector.is_automatic_message_active)
        self.assertEqual(self.sector.automatic_message_text, text)

    def test_delete_sector_with_right_project_token(self):
        """
        Verify if the endpoint for delete sector is working with correctly.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class RoomsExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.queue_1 = Queue.objects.get(uuid="f2519480-7e58-4fc4-9894-9ab1769e29cf")

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room(self, mock_get_room, mock_is_attending):
        mock_get_room.return_value = None
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-40cd-b480-b45594b70299",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room_with_external_uuid(
        self, mock_get_room, mock_is_attending
    ):
        mock_get_room.return_value = None
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "aec9f84e-3dcd-11ed-b878-0242ac190012",
                "name": "external generator",
                "email": "generator@weni.ai",
                "phone": "+558498984312",
                "custom_fields": {"age": "35"},
            },
        }
        response = client.post(url, data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["contact"]["name"], "external generator")
        self.assertEqual(
            response.data["contact"]["external_id"],
            "aec9f84e-3dcd-11ed-b878-0242ac190012",
        )

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room_editing_contact(
        self, mock_get_room, mock_is_attending
    ):
        mock_get_room.return_value = None
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        contact = Contact.objects.exclude(rooms__is_active=True).first()
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": contact.external_id,
                "name": "gaules",
                "email": "gaulesr@weni.ai",
                "phone": "+5511985543332",
                "custom_fields": {
                    "age": "40",
                    "prefered_game": "cs-go",
                    "job": "streamer",
                },
            },
        }
        response = client.post(url, data=data, format="json")
        contact.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(contact.name, "gaules")
        self.assertEqual(
            contact.custom_fields,
            {
                "age": "40",
                "prefered_game": "cs-go",
                "job": "streamer",
            },
        )


class MsgsExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")

    def test_create_external_msgs(self):
        url = reverse("external_message-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "room": self.room.uuid,
            "text": "olá.",
            "direction": "incoming",
            "attachments": [{"content_type": "string", "url": "http://example.com"}],
        }
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
