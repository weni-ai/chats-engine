import time
import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room


class DashboardTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.queue_1 = Queue.objects.get(uuid="f341417b-5143-4469-a99d-f141a0676bd4")
        self.manager_user = User.objects.get(pk=7)
        self.login_token = Token.objects.get_or_create(user=self.manager_user)[0]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.patcher = patch(
            "chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room",
            return_value=None,
        )
        cls.mocked_function = cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()
        super().tearDownClass()

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    def test_create_room_metrics(self, mock_is_attending):
        """
        Verify if the room metric its created when a room is created.
        """
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )

        data = {
            "queue_uuid": "f341417b-5143-4469-a99d-f141a0676bd4",
            "contact": {
                "external_id": str(uuid.uuid4()),
                "name": "Test Contact",
                "email": "test@example.com",
                "phone": "+1234567890",
                "custom_fields": {},
            },
        }

        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        room_uuid = response.data["uuid"]
        room_metric = RoomMetrics.objects.filter(room__uuid=room_uuid).exists()
        self.assertEqual(room_metric, True)

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    def test_interaction_time_metric_calc(self, mock_is_attending):
        """
        Verify if the interaction_time of a room metric its calculated correctly.
        """
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )

        data = {
            "queue_uuid": "f341417b-5143-4469-a99d-f141a0676bd4",
            "contact": {
                "external_id": str(uuid.uuid4()),
                "name": "Test Contact",
                "email": "test@example.com",
                "phone": "+1234567890",
                "custom_fields": {},
            },
        }

        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        room_created = Room.objects.get(uuid=response.data["uuid"])
        room_created.user = self.manager_user
        room_created.save()

        time.sleep(3)

        url_close = f"/v1/room/{room_created.uuid}/close/"
        close_client = self.client
        close_client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data_close = {"tags": []}
        client.patch(url_close, data=data_close, format="json")

        room_closed = Room.objects.get(queue_id=data["queue_uuid"])
        metric = RoomMetrics.objects.get(room=room_closed)

        self.assertEqual(metric.interaction_time, 3)

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    def test_message_response_time_metric_calc(self, mock_is_attending):
        """
        Verify if the message_response_time of a room metric its calculated correctly.
        """
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )

        data = {
            "queue_uuid": "f341417b-5143-4469-a99d-f141a0676bd4",
            "contact": {
                "external_id": str(uuid.uuid4()),
                "name": "Test Message Response",
                "email": "test@example.com",
                "phone": "+1234567890",
                "custom_fields": {},
            },
        }

        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        room_created = Room.objects.get(uuid=response.data["uuid"])
        room_created.user = self.manager_user
        room_created.save()

        msg_contact_client = self.client
        msg_contact_client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        url_contact_message = "/v1/external/msgs/"

        message_data = {
            "room": str(room_created.uuid),
            "text": "teste criação",
            "direction": "incoming",
            "attachments": [],
        }
        msg_contact_client.post(url_contact_message, data=message_data, format="json")

        time.sleep(3)

        msg_user_client = self.client
        msg_user_client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        url_user_message = "/v1/msg/"

        message_user_data = {
            "room": str(room_created.pk),
            "user_email": str(self.manager_user),
            "text": "teste criação resposta",
        }
        msg_user_client.post(url_user_message, data=message_user_data, format="json")

        url_close = f"/v1/room/{room_created.uuid}/close/"
        close_client = self.client
        close_client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data_close = {"tags": []}
        client.patch(url_close, data=data_close, format="json")

        room_closed = Room.objects.get(queue_id=data["queue_uuid"])
        metric = RoomMetrics.objects.get(room=room_closed)

        self.assertEqual(metric.message_response_time, 3)

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    def test_waiting_time_metric_calc(self, mock_is_attending):
        """
        Verify if the waiting_time of a room metric its calculated correctly.
        """
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )

        data = {
            "queue_uuid": "f341417b-5143-4469-a99d-f141a0676bd4",
            "contact": {
                "external_id": str(uuid.uuid4()),
                "name": "Test Waiting Time",
                "email": "test@example.com",
                "phone": "+1234567890",
            },
        }

        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        room_created = Room.objects.get(uuid=response.data["uuid"])

        room_created.is_waiting = True
        room_created.save()

        metric = room_created.metric
        metric.waiting_time = 3
        metric.save()

        metric.refresh_from_db()
        self.assertEqual(metric.waiting_time, 3)

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    def test_dashboard_model_name_property(self, mock_is_attending):
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )

        data = {
            "queue_uuid": "f341417b-5143-4469-a99d-f141a0676bd4",
            "contact": {
                "external_id": str(uuid.uuid4()),
                "name": "Test Dashboard Contact",
                "email": "test@example.com",
                "phone": "+1234567890",
                "custom_fields": {},
            },
        }

        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        room_metric = RoomMetrics.objects.get(room__uuid=response.data["uuid"])
        self.assertEqual(room_metric.__class__.__name__, "RoomMetrics")
