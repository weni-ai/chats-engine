from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from chats.apps.dashboard.models import RoomMetrics
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room

import time


class DashboardTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.queue_1 = Queue.objects.get(uuid="f341417b-5143-4469-a99d-f141a0676bd4")

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
                "external_id": "e3955fd5-5705-40cd-b480-b45594b70282",
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
        url = reverse("external_rooms-list")
        print(url)
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-40cd-b480-b45594b70282",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        client.post(url, data=data, format="json")
        room_created = Room.objects.get(queue_id=data["queue_uuid"])
        time.sleep(3)
        # print(room_created.uuid)
        url_close = f"/v1/external/rooms/{room_created.uuid}/close/"
        client.patch(url_close, data="", format="json")
        # print(url_close)
        # print(room_created)

        room_closed = Room.objects.get(queue_id=data["queue_uuid"])

        a = RoomMetrics.objects.filter(room=room_closed).values()
        print(a)

        difference = room_closed.ended_at - room_created.created_on

        difference_metric_value = RoomMetrics.objects.filter(room=room_closed).values(
            "interaction_time"
        )
        print("abertura", room_created.created_on)
        print("fechamento", room_closed.ended_at)
        print(difference)
