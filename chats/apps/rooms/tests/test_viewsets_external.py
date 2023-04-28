from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.queues.models import Queue


class RoomsExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.queue_1 = Queue.objects.get(uuid="f341417b-5143-4469-a99d-f141a0676bd4")

    def _create_room(self, token: str, data: dict):
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        return client.post(url, data=data, format="json")

    def test_create_external_room(self):
        """
        Verify if the endpoint for create external room it is working correctly.
        """
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
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_external_room_with_external_uuid(self):
        """
        Verify if the endpoint for create external room it is working correctly, passing custom fields.
        """
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
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)
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
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-40cd-b480-b45594b70282",
                "name": "gaules",
                "email": "gaulesr@weni.ai",
                "phone": "+5511985543332",
                "urn": "whatsapp:5521917078266?auth=eyJhbGciOiAiSFM",
                "custom_fields": {
                    "age": "40",
                    "prefered_game": "cs-go",
                    "job": "streamer",
                },
            },
        }

        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["contact"]["name"], "gaules")
        self.assertEqual(response.data["urn"], "whatsapp:5521917078266")
        self.assertEqual(response.data["contact"]["custom_fields"]["age"], "40")
        self.assertEqual(
            response.data["contact"]["custom_fields"]["prefered_game"], "cs-go"
        )
        self.assertEqual(response.data["contact"]["custom_fields"]["job"], "streamer")

    def test_is_anon_true_wont_save_urn(self):
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-40cd-b480-b45594b70282",
                "name": "gaules",
                "email": "gaulesr@weni.ai",
                "phone": "+5511985543332",
                "urn": "whatsapp:5521917078266?auth=eyJhbGciOiAiSFM",
                "custom_fields": {
                    "age": "40",
                    "prefered_game": "cs-go",
                    "job": "streamer",
                },
            },
        }
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.get("urn"), None)


class RoomsFlowStartExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.queue_1 = Queue.objects.get(uuid="f2519480-7e58-4fc4-9894-9ab1769e29cf")
        self.project = self.queue_1.sector.project
        self.room = self.queue_1.rooms.filter(
            is_active=True, user__isnull=False
        ).first()
        self.permission = self.project.permissions.get(user=self.room.user)
        self.room_flowstart = self.project.flowstarts.create(
            flow="a75d0853-e4e8-48bd-bdb5-f8685a0d5026",
            permission=self.permission,
            room=self.room,
        )
        self.room_flowstart.references.create(
            receiver_type="contact", external_id=str(self.room.contact.external_id)
        )

        self.contact_and_group_flowstart = self.project.flowstarts.create(
            flow="dc531e97-95ca-457c-8796-70e15d30c2db",
            permission=self.permission,
        )
        self.contact_reference = self.contact_and_group_flowstart.references.create(
            receiver_type="contact", external_id="7848de87-aaa5-4ce2-a1df-ba98e78a50d1"
        )
        self.group_reference = self.contact_and_group_flowstart.references.create(
            receiver_type="group", external_id="83623269-19c0-4878-9dee-bace53fc6a6d"
        )

    def _create_room(self, token: str, data: dict):
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        return client.post(url, data=data, format="json")

    def test_create_room_with_flow_start(self):
        flow_start = self.room_flowstart
        data = {
            "queue_uuid": str(self.queue_1.pk),
            "contact": {
                "external_id": self.room.contact.external_id,
                "name": "John Doe",
                "urn": "whatsapp:5521917078236?auth=eyJhbGciOiAiSFM",
            },
            "flow_uuid": flow_start.flow,
        }
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)
        flow_start.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json().get("uuid"), str(self.room.pk))
        self.assertTrue(flow_start.is_deleted)

    def test_create_room_with_deleted_flow_start(self):
        flow_start = self.room_flowstart
        flow_start.is_deleted = True
        flow_start.save()
        data = {
            "queue_uuid": str(self.queue_1.pk),
            "contact": {
                "external_id": self.room.contact.external_id,
                "name": "John Doe",
                "urn": "whatsapp:5521917078236?auth=eyJhbGciOiAiSFM",
            },
            "flow_uuid": flow_start.flow,
        }
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json().get("detail"),
            "The contact already have an open room in the especified queue",
        )

    def test_create_room_with_contact_flow_start_with_offline_user(self):
        data = {
            "queue_uuid": str(self.queue_1.pk),
            "contact": {
                "external_id": self.contact_reference.external_id,
                "name": "Foo bar",
                "urn": "whatsapp:5521917078236?auth=eyJhbGciOiAiSFM",
            },
            "flow_uuid": self.contact_and_group_flowstart.flow,
        }
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(
            response.json().get("user"),
        )

    def test_create_room_with_contact_flow_start_with_online_user(self):
        permission = self.permission
        permission.status = "ONLINE"
        permission.save()
        data = {
            "queue_uuid": str(self.queue_1.pk),
            "contact": {
                "external_id": self.contact_reference.external_id,
                "name": "Foo bar",
                "urn": "whatsapp:5521917078236?auth=eyJhbGciOiAiSFM",
            },
            "flow_uuid": self.contact_and_group_flowstart.flow,
        }
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json().get("user").get("email"),
            permission.user.email,
        )

    def test_create_room_with_group_flow_start_with_online_user(self):
        permission = self.permission
        permission.status = "ONLINE"
        permission.save()
        data = {
            "queue_uuid": str(self.queue_1.pk),
            "contact": {
                "external_id": "387908e4-f9cf-475d-86a8-65a983d91cc0",
                "name": "Foo bar",
                "urn": "whatsapp:5521917078236?auth=eyJhbGciOiAiSFM",
                "groups": [
                    {
                        "uuid": self.group_reference.external_id,
                    },
                    {
                        "uuid": "d7a71baa-0c6a-42bd-a220-ff028ae58ad6",
                    },
                ],
            },
            "flow_uuid": self.contact_and_group_flowstart.flow,
        }
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json().get("user").get("email"),
            permission.user.email,
        )

    def test_create_room_with_group_flow_start_with_offline_user(self):

        data = {
            "queue_uuid": str(self.queue_1.pk),
            "contact": {
                "external_id": "387908e4-f9cf-475d-86a8-65a983d91cc0",
                "name": "Foo bar",
                "urn": "whatsapp:5521917078236?auth=eyJhbGciOiAiSFM",
                "groups": [
                    {
                        "uuid": self.group_reference.external_id,
                    },
                    {
                        "uuid": "d7a71baa-0c6a-42bd-a220-ff028ae58ad6",
                    },
                ],
            },
            "flow_uuid": self.contact_and_group_flowstart.flow,
        }
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(
            response.json().get("user"),
        )
