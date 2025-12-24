from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework.response import Response
from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, RoomRoutingType
from chats.apps.queues.models import Queue, User
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from unittest import mock
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission

from chats.apps.api.utils import create_user_and_token


class RoomsExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.queue_1 = Queue.objects.get(uuid="f341417b-5143-4469-a99d-f141a0676bd4")

    def _create_room(self, token: str, data: dict, token_type: str = "Bearer"):
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"{token_type} {token}")

        return client.post(url, data=data, format="json")

    def _close_room(self, token: str, room_id: str):
        url = reverse("external_rooms-close", kwargs={"uuid": room_id})
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        return client.put(url, format="json")

    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.WeniOIDCAuthenticationBackend.get_userinfo"
    )
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room_with_internal_token(
        self, mock_get_room, mock_get_userinfo
    ):
        # Mock the userinfo response
        mock_get_userinfo.return_value = {
            "sub": "test_user",
            "email": "test_user@example.com",
            "preferred_username": "test_user",
            "given_name": "Test",
            "family_name": "User",
        }
        mock_get_room.return_value = None

        user, token = create_user_and_token("test_user")

        permission, created = Permission.objects.get_or_create(
            codename="can_communicate_internally",
            content_type=ContentType.objects.get_for_model(User),
        )
        user.user_permissions.add(permission)
        self.client.force_authenticate(user)

        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-60cd-b480-b45594b70282",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }

        response = self._create_room(token, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @mock.patch(
        "chats.apps.api.v1.internal.permissions.ModuleHasPermission.has_permission",
    )
    def test_cannot_create_room_with_token_without_can_communicate_internally_perm(
        self, mock_has_permission
    ):
        mock_has_permission.return_value = False
        user, token = create_user_and_token("test_user")
        self.client.force_authenticate(user)

        data = {
            "queue_uuid": str(self.queue_1.uuid),
        }
        response = self._create_room(token, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_has_permission.assert_called_once()

    @override_settings(INTERNAL_API_TOKEN="dummy-token")
    def test_create_external_room_with_internal_api_token(self):
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-60cd-b480-b45594b70282",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        response = self._create_room("dummy-token", data, token_type="Token")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(INTERNAL_API_TOKEN="dummy-token")
    def test_create_external_room_with_internal_api_token_with_invalid_token(self):
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-60cd-b480-b45594b70282",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }

        response = self._create_room("invalid-token", data, token_type="Token")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room(self, mock_get_room, mock_is_attending):
        """
        Verify if the endpoint for create external room it is working correctly.
        """
        mock_get_room.return_value = None
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-60cd-b480-b45594b70282",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        room = Room.objects.get(uuid=response.data.get("uuid"))

        mock_get_room.assert_called_once_with(room)
        self.assertTrue(room.is_billing_notified)

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room_with_external_uuid(
        self, mock_get_room, mock_is_attending
    ):
        """
        Verify if the endpoint for create external room it is working correctly, passing custom fields.
        """
        mock_get_room.return_value = None
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

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room_editing_contact(
        self, mock_get_room, mock_is_attending
    ):
        """
        Verify if the endpoint for edit external room it is working correctly.
        """
        mock_get_room.return_value = None
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-30cd-b480-b45594b70282",
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

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_is_anon_true_wont_save_urn(self, mock_get_room, mock_is_attending):
        mock_get_room.return_value = None
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-55cd-b480-b45594b70282",
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
            "is_anon": True,
        }
        response = self._create_room("f3ce543e-d77e-4508-9140-15c95752a380", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.get("urn"), None)

    def test_close_room(self):
        room = Room.objects.create(queue=self.queue_1)

        response = self._close_room("f3ce543e-d77e-4508-9140-15c95752a380", room.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.WeniOIDCAuthenticationBackend.get_userinfo"
    )
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_close_room_with_internal_token(self, mock_get_room, mock_get_userinfo):
        mock_get_room.return_value = None
        room = Room.objects.create(queue=self.queue_1)
        mock_get_userinfo.return_value = {
            "sub": "test_user",
            "email": "test_user@example.com",
            "preferred_username": "test_user",
            "given_name": "Test",
            "family_name": "User",
        }

        user, token = create_user_and_token("test_user")
        permission, created = Permission.objects.get_or_create(
            codename="can_communicate_internally",
            content_type=ContentType.objects.get_for_model(User),
        )
        user.user_permissions.add(permission)
        self.client.force_authenticate(user)

        response = self._close_room(token, room.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch(
        "chats.apps.api.v1.internal.permissions.ModuleHasPermission.has_permission",
        return_value=False,
    )
    def test_cannot_close_room_with_token_without_can_communicate_internally_perm(
        self, mock_has_permission
    ):
        mock_has_permission.return_value = False
        user, token = create_user_and_token("test_user")
        self.client.force_authenticate(user)

        room = Room.objects.create(queue=self.queue_1)

        response = self._close_room(token, room.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_has_permission.assert_called_once()


class RoomsQueuePriorityExternalTests(APITestCase):
    def setUp(self) -> None:
        self.project = Project.objects.create(
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
            timezone="America/Sao_Paulo",
        )
        self.sector = Sector.objects.create(
            project=self.project, rooms_limit=1, work_start="00:00", work_end="23:59"
        )
        self.queue = Queue.objects.create(sector=self.sector)

    def create_room(self, data: dict) -> Response:
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.project.external_token.uuid}"
        )

        return client.post(url, data=data, format="json")

    @patch("chats.apps.api.v1.external.rooms.serializers.start_queue_priority_routing")
    @patch("chats.apps.api.v1.external.rooms.serializers.logger")
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_room_with_queue_priority_when_queue_is_empty_and_no_user_is_online(
        self,
        mock_get_room,
        mock_logger,
        mock_start_queue_priority_routing,
    ):
        mock_get_room.return_value = None
        mock_start_queue_priority_routing.return_value = None
        data = {
            "queue_uuid": str(self.queue.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-55cd-b480-b45594b70282",
                "name": "kallil",
                "email": "kallil@email.com",
                "phone": "+5511985543332",
                "urn": "whatsapp:5521917078266?auth=eyJhbGciOiAiSFM",
                "custom_fields": {},
            },
        }
        response = self.create_room(data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data.get("user"))

        mock_start_queue_priority_routing.assert_not_called()
        mock_logger.assert_not_called()

    @patch("chats.apps.api.v1.external.rooms.serializers.start_queue_priority_routing")
    @patch("chats.apps.api.v1.external.rooms.serializers.logger")
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_room_with_queue_priority_when_queue_is_empty_and_user_is_online(
        self,
        mock_get_room,
        mock_logger,
        mock_start_queue_priority_routing,
    ):
        mock_get_room.return_value = None
        mock_start_queue_priority_routing.return_value = None

        user = User.objects.create(
            email="user@email.com",
        )
        permission = self.project.permissions.create(user=user, status="ONLINE")
        self.queue.authorizations.create(permission=permission, role=1)

        data = {
            "queue_uuid": str(self.queue.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-55cd-b480-b45594b70282",
                "name": "kallil",
                "email": "kallil@email.com",
                "phone": "+5511985543332",
                "urn": "whatsapp:5521917078266?auth=eyJhbGciOiAiSFM",
                "custom_fields": {},
            },
        }
        response = self.create_room(data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get("user").get("email"), user.email)

        mock_start_queue_priority_routing.assert_not_called()
        mock_logger.assert_not_called()

    @patch("chats.apps.api.v1.external.rooms.serializers.start_queue_priority_routing")
    @patch("chats.apps.api.v1.external.rooms.serializers.logger")
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_room_with_queue_priority_when_user_is_online_but_queue_is_not_empty(
        self,
        mock_get_room,
        mock_logger,
        mock_start_queue_priority_routing,
    ):
        mock_get_room.return_value = None
        mock_start_queue_priority_routing.return_value = None

        user = User.objects.create(
            email="user@email.com",
        )
        permission = self.project.permissions.create(user=user, status="ONLINE")
        self.queue.authorizations.create(permission=permission, role=1)

        Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(
                external_id="e3955fd5-5705-55cd-b480-b45594b70282",
            ),
            user=user,
            is_active=True,
        )

        # Room in waiting in the queue
        Room.objects.create(
            queue=self.queue,
            contact=Contact.objects.create(
                external_id="e581f4c4-5a3d-47f3-bdc6-158efd6062b5",
            ),
            is_active=True,
        )

        current_queue_size = self.queue.rooms.filter(
            is_active=True, user__isnull=True
        ).count()

        self.assertEqual(current_queue_size, 1)

        data = {
            "queue_uuid": str(self.queue.uuid),
            "contact": {
                "external_id": "8b411ef7-46b2-414b-9ee0-6732301b257b",
                "name": "kallil",
                "email": "kallil@email.com",
                "phone": "+5511985543332",
                "urn": "whatsapp:5521917078266?auth=eyJhbGciOiAiSFM",
                "custom_fields": {},
            },
        }
        response = self.create_room(data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data.get("user"))

        mock_start_queue_priority_routing.assert_called_once_with(self.queue)
        mock_logger.info.assert_any_call(
            "Calling start_queue_priority_routing for queue %s from get_room_user because the queue is not empty",
            self.queue.uuid,
        )


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

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_room_with_flow_start(self, mock_get_room, mock_is_attending):
        mock_get_room.return_value = None
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

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_room_with_deleted_flow_start(
        self, mock_get_room, mock_is_attending
    ):
        mock_get_room.return_value = None
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
        self.assertIn(
            response.json().get("detail"),
            {
                "The contact already have an open room in the project",
                "The contact already have an open room in the especified queue",
            },
        )

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_room_with_contact_flow_start_with_offline_user(
        self, mock_get_room, mock_is_attending
    ):
        mock_get_room.return_value = None
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

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_room_with_contact_flow_start_with_online_user(
        self, mock_get_room, mock_is_attending
    ):
        mock_get_room.return_value = None
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

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_room_with_group_flow_start_with_online_user(
        self, mock_get_room, mock_is_attending
    ):
        mock_get_room.return_value = None
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

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_room_with_group_flow_start_with_offline_user(
        self, mock_get_room, mock_is_attending
    ):
        mock_get_room.return_value = None
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


class RoomsAgentExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json", "chats/fixtures/fixture_room.json"]

    def _update_room(self, ticket_id: str, permission_token: str, data: dict):
        url = reverse("external_roomagent-detail", kwargs={"pk": ticket_id})
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {permission_token}")

        return client.patch(url, data=data, format="json")

    @patch("chats.apps.rooms.models.FlowRESTClient.update_ticket_assignee")
    def test_add_agent_to_queued_room(self, mock_update_ticket_assignee):
        mock_update_ticket_assignee.return_value = None
        data = {
            "agent": "foobar@chats.weni.ai",
        }
        response = self._update_room(
            "66a47111-6e6f-43b3-9fdc-a92a18bc57d2",
            "e416fd45-2896-43a5-bd7a-5067f03c77fa",
            data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_agent_outside_project_to_queued_room(self):
        data = {
            "agent": "agentqueue@chats.weni.ai",
        }
        response = self._update_room(
            "66a47111-6e6f-43b3-9fdc-a92a18bc57d2",
            "e416fd45-2896-43a5-bd7a-5067f03c77fa",
            data,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_agent_to_queued_room_with_agent_token(self):
        data = {
            "agent": "foobar@chats.weni.ai",
        }
        response = self._update_room(
            "66a47111-6e6f-43b3-9fdc-a92a18bc57d2",
            "25b32a73-c32a-4c38-85a7-f07dcb8389e5",
            data,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_remove_agent_to_queued_room(self):
        data = {}
        response = self._update_room(
            "66a47111-6e6f-43b3-9fdc-a92a18bc57d2",
            "e416fd45-2896-43a5-bd7a-5067f03c77fa",
            data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_agent_to_queued_room(self):
        data = {
            "agent": "foobar@chats.weni.ai",
        }
        response = self._update_room(
            "1c830ac0-1ba7-49f9-b8c8-b96af41d4213",
            "e416fd45-2896-43a5-bd7a-5067f03c77fa",
            data,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_agent_to_closed_room(self):
        data = {
            "agent": "foobar@chats.weni.ai",
        }
        response = self._update_room(
            "ac6322ca-4a5b-4e5f-bb00-050c60e93b0b",
            "e416fd45-2896-43a5-bd7a-5067f03c77fa",
            data,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_agent_to_nonexistent_room(self):
        data = {
            "agent": "foobar@chats.weni.ai",
        }
        response = self._update_room(
            "ac6667ca-4a5b-4e5f-bb00-050c60e93b0b",
            "e416fd45-2896-43a5-bd7a-5067f03c77fa",
            data,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RoomsRoutingExternalTests(APITestCase):
    fixtures = [
        "chats/fixtures/fixture_sector.json",
    ]

    def _create_room(self, token: str, data: dict):
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        return client.post(url, data=data, format="json")

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room_can_open_offline(
        self, mock_get_room, mock_is_attending
    ):
        mock_get_room.return_value = None
        data = {
            "queue_uuid": "8590ad29-5629-448c-bfb6-1bfd5219b8ec",
            "contact": {
                "external_id": "953fdcc9-1f6f-4abd-b90e-10a35c1cc825",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        response = self._create_room("b5fab78a-4836-468c-96c4-f5b0bba3303a", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    def test_create_external_room_cannot_open_offline(self, mock_is_attending):
        data = {
            "queue_uuid": "605e21b0-4177-4eae-9cfb-529d9972a192",
            "contact": {
                "external_id": "a5ff0cd3-0bcd-4e91-8120-8718128cb1d9",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        response = self._create_room("b5fab78a-4836-468c-96c4-f5b0bba3303a", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RoomsExternalProtocolTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.queue_1 = Queue.objects.get(uuid="f341417b-5143-4469-a99d-f141a0676bd4")
        self.user, self.token = create_user_and_token("test_user")

        permission, _ = Permission.objects.get_or_create(
            codename="can_communicate_internally",
            content_type=ContentType.objects.get_for_model(User),
        )
        self.user.user_permissions.add(permission)
        self.client.force_authenticate(self.user)

        self.url = reverse("external_rooms-list")

    def _create_room(self, data: dict):
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        return client.post(self.url, data=data, format="json")

    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    @patch(
        "chats.apps.accounts.authentication.drf.backends.WeniOIDCAuthenticationBackend.get_userinfo"
    )
    def test_protocol_comes_in_body(self, mock_get_userinfo, mock_get_room):
        mock_get_userinfo.return_value = {"sub": "test_user"}
        mock_get_room.return_value = None

        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {"external_id": "contact-1", "name": "Foo"},
            "protocol": "PROTO_BODY",
            "custom_fields": {"protocol": "PROTO_CUSTOM"},
        }

        response = self._create_room(data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        room = Room.objects.get(uuid=response.data["uuid"])
        self.assertEqual(room.protocol, "PROTO_BODY")

    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    @patch(
        "chats.apps.accounts.authentication.drf.backends.WeniOIDCAuthenticationBackend.get_userinfo"
    )
    def test_protocol_empty_in_body_uses_custom(self, mock_get_userinfo, mock_get_room):
        mock_get_userinfo.return_value = {"sub": "test_user"}
        mock_get_room.return_value = None

        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {"external_id": "contact-2", "name": "Bar"},
            "protocol": "",
            "custom_fields": {"protocol": "PROTO_CUSTOM"},
        }

        response = self._create_room(data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        room = Room.objects.get(uuid=response.data["uuid"])
        self.assertEqual(room.protocol, "PROTO_CUSTOM")

    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    @patch(
        "chats.apps.accounts.authentication.drf.backends.WeniOIDCAuthenticationBackend.get_userinfo"
    )
    def test_protocol_absent_in_body_uses_custom(
        self, mock_get_userinfo, mock_get_room
    ):
        mock_get_userinfo.return_value = {"sub": "test_user"}
        mock_get_room.return_value = None

        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {"external_id": "contact-3", "name": "Baz"},
            "custom_fields": {"protocol": "PROTO_CUSTOM"},
        }

        response = self._create_room(data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        room = Room.objects.get(uuid=response.data["uuid"])
        self.assertEqual(room.protocol, "PROTO_CUSTOM")
