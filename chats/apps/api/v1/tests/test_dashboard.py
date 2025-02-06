import time

from django.urls import reverse
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

    def test_create_room_metrics(self):
        """
        Verify if the room metric its created when a room is created.
        """
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-70cd-b480-b45594b70282",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        client.post(url, data=data, format="json")
        room_metric = RoomMetrics.objects.filter(
            room__queue__uuid=data["queue_uuid"]
        ).exists()
        self.assertEqual(room_metric, True)

    def test_interaction_time_metric_calc(self):
        """
        Verify if the interaction_time of a room metric its calculated correctly.
        """
        url = "/v1/external/rooms/"
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "user_email": str(self.manager_user),
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-55cd-b480-b45594b70282",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        client.post(url, data=data, format="json")
        room_created = Room.objects.get(queue_id=data["queue_uuid"])
        room_created.user = self.manager_user
        room_created.save()

        time.sleep(3)

        url_close = f"/v1/room/{room_created.uuid}/close/"
        close_client = self.client
        close_client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data_close = {
            "tags": [
                "f4b8aa78-7735-4dd2-9999-941ebb8e4e35",
                "1a84b46e-0f91-41da-ac9d-a68c0b9753ab",
            ]
        }
        client.patch(url_close, data=data_close, format="json")

        room_closed = Room.objects.get(queue_id=data["queue_uuid"])
        metric = RoomMetrics.objects.get(room=room_closed)

        self.assertEqual(metric.interaction_time, 3)

    def test_message_response_time_metric_calc(self):
        """
        Verify if the message_response_time of a room metric its calculated correctly.
        """
        url = "/v1/external/rooms/"
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "user_email": str(self.manager_user),
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-90cd-b480-b45594b70282",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        client.post(url, data=data, format="json")
        room_created = Room.objects.get(queue_id=data["queue_uuid"])
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
        data_close = {
            "tags": [
                "f4b8aa78-7735-4dd2-9999-941ebb8e4e35",
                "1a84b46e-0f91-41da-ac9d-a68c0b9753ab",
            ]
        }
        client.patch(url_close, data=data_close, format="json")

        room_closed = Room.objects.get(queue_id=data["queue_uuid"])
        metric = RoomMetrics.objects.get(room=room_closed)

        self.assertEqual(metric.message_response_time, 3)

    def test_dashboard_model_name_property(self):
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-80cd-b480-b45594b70282",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        client.post(url, data=data, format="json")
        room_metric = RoomMetrics.objects.get(room__queue__uuid=data["queue_uuid"])

        self.assertEqual(room_metric.__str__(), "FRONTEND")
