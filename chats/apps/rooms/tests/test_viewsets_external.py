from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.queues.models import Queue


class RoomsExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.queue_1 = Queue.objects.get(uuid="f341417b-5143-4469-a99d-f141a0676bd4")

    def test_create_external_room(self):
        """
        Verify if the endpoint for create external room it is working correctly.
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
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_external_room_with_external_uuid(self):
        """
        Verify if the endpoint for create external room it is working correctly, passing custom fields.
        """
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "aec9f84e-3dcd-11ed-b878-0242ac120002",
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
            "aec9f84e-3dcd-11ed-b878-0242ac120002",
        )

    def test_create_external_room_editing_contact(self):
        """
        Verify if the endpoint for edit external room it is working correctly.
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["contact"]["name"], "gaules")
        self.assertEqual(response.data["contact"]["custom_fields"]["age"], "40")
        self.assertEqual(
            response.data["contact"]["custom_fields"]["prefered_game"], "cs-go"
        )
        self.assertEqual(response.data["contact"]["custom_fields"]["job"], "streamer")
