import uuid
from datetime import time
from unittest.mock import patch, PropertyMock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.ai_features.history_summary.models import (
    HistorySummary,
    HistorySummaryStatus,
)
from chats.apps.api.utils import create_contact, create_user_and_token
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.projects.models.models import RoomRoutingType
from chats.apps.projects.tests.decorators import with_project_permission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.queues.tests.decorators import with_queue_authorization
from chats.apps.rooms.models import Room, RoomPin
from chats.apps.rooms.services import RoomsReportService
from chats.apps.rooms.tests.decorators import with_room_user
from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag
from chats.apps.sectors.tests.decorators import with_sector_authorization
from chats.core.cache import CacheClient

User = get_user_model()


class RoomTests(APITestCase):
    def setUp(self):
        # USERS
        self.owner, self.owner_token = create_user_and_token("owner")

        self.manager, self.manager_token = create_user_and_token("manager")
        self.manager_2, self.manager_2_token = create_user_and_token("manager")
        self.manager_3, self.manager_3_token = create_user_and_token("manager 3")

        self.agent, self.agent_token = create_user_and_token("agent")
        self.agent_2, self.agent_2_token = create_user_and_token("agent2")

        # CONTACTS
        self.contact = create_contact("Contact", "contatc@mail.com", "offline", {})
        self.contact_2 = create_contact("Contact2", "contatc2@mail.com", "offline", {})
        self.contact_3 = create_contact("Contact3", "contatc3@mail.com", "offline", {})

        # PROJECTS
        self.project = Project.objects.create(name="Test Project")
        self.project_2 = Project.objects.create(name="Test Project")

        # PROJECT AUTHORIZATIONS
        self.owner_auth = self.project.permissions.create(
            user=self.owner, role=ProjectPermission.ROLE_ADMIN
        )

        self.manager_perm = self.project.permissions.create(user=self.manager, role=2)
        self.manager2_perm = self.project.permissions.get(user=self.manager_2)
        self.agent_perm = self.project.permissions.create(
            user=self.agent, role=ProjectPermission.ROLE_ATTENDANT
        )
        self.agent2_perm = self.project.permissions.create(
            user=self.agent_2, role=ProjectPermission.ROLE_ATTENDANT
        )

        # SECTORS
        self.sector_1 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_2 = Sector.objects.get(
            name="Test Sector",
            project=self.project,
        )
        self.sector_3 = Sector.objects.create(
            name="Sector on project 2",
            project=self.project_2,
            rooms_limit=1,
            work_start="07:00",
            work_end="17:00",
        )

        # SECTOR AUTHORIZATIONS
        self.manager_auth = self.sector_1.set_user_authorization(
            self.manager_perm, role=SectorAuthorization.ROLE_MANAGER
        )
        self.manager_2_auth = self.sector_2.set_user_authorization(
            self.manager2_perm, role=SectorAuthorization.ROLE_MANAGER
        )
        self.manager_2_auth_1 = self.sector_3.set_user_authorization(
            self.manager_perm, role=SectorAuthorization.ROLE_MANAGER
        )

        # QUEUES
        self.queue_1 = Queue.objects.create(name="Q1", sector=self.sector_1)
        self.queue_2 = Queue.objects.create(name="Q2", sector=self.sector_1)
        self.queue_3 = Queue.objects.create(name="Q3", sector=self.sector_2)

        # QUEUE AUTHORIZATIONS
        self.agent_1_auth = self.queue_1.authorizations.create(
            permission=self.agent_perm, role=QueueAuthorization.ROLE_AGENT
        )
        self.agent_2_auth = self.queue_2.authorizations.create(
            permission=self.agent2_perm, role=QueueAuthorization.ROLE_AGENT
        )
        self.agent_2_auth_2 = self.queue_3.authorizations.create(
            permission=self.agent2_perm, role=QueueAuthorization.ROLE_AGENT
        )

        # ROOMS
        self.room_1 = Room.objects.create(
            contact=self.contact,
            queue=self.queue_1,
            user=self.agent,
            project_uuid=str(self.project.uuid),
        )
        self.room_2 = Room.objects.create(
            contact=self.contact_2,
            queue=self.queue_2,
            project_uuid=str(self.project.uuid),
        )
        self.room_3 = Room.objects.create(
            contact=self.contact_3,
            queue=self.queue_3,
            project_uuid=str(self.project.uuid),
        )

    def _request_list_rooms(self, token, data: dict):
        url = reverse("room-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = client.get(url, data=data)
        results = response.json().get("results")
        return response, results

    def _ok_list_rooms(self, token, rooms: list, data: dict):
        response, results = self._request_list_rooms(token, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), len(rooms))

        for result in results:
            self.assertIn(result.get("uuid"), rooms)

    def _not_ok_list_rooms(self, token, data: dict):
        response, _ = self._request_list_rooms(token, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 0)

    def test_list_rooms_given_agents(self):
        self._ok_list_rooms(
            self.agent_token,
            [str(self.room_1.uuid)],
            {"project": self.project.uuid},
        )
        self._ok_list_rooms(
            self.agent_2_token,
            [str(self.room_2.uuid), str(self.room_3.uuid)],
            {"project": self.project.uuid},
        )

    def test_list_rooms_with_manager_and_admin_token(self):
        self._ok_list_rooms(
            self.manager_token,
            [str(self.room_2.uuid), str(self.room_3.uuid)],
            {"project": self.project.uuid},
        )

        self._ok_list_rooms(
            self.owner_token,
            [str(self.room_2.uuid), str(self.room_3.uuid)],
            {"project": self.project.uuid},
        )

    def test_list_rooms_with_not_permitted_manager_token(self):
        self._not_ok_list_rooms(
            self.manager_3_token,
            {"project": self.project.uuid},
        )


class RoomMessagesTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.room = Room.objects.filter(
            is_active=True, messages__contact__isnull=False
        ).first()
        self.agent_token = self.room.user.auth_token.pk

    def _update_message_status(self, token: str, data: dict):
        url = reverse("room-bulk_update_msgs", args=[str(self.room.pk)])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        return client.patch(url, data=data, format="json")

    def test_read_all_messages(self):
        unread_messages_count_old = self.room.messages.filter(seen=False).count()

        data = {"seen": True}
        response = self._update_message_status(token=self.agent_token, data=data)

        unread_messages_count_new = self.room.messages.filter(seen=False).count()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(unread_messages_count_new, unread_messages_count_old)
        self.assertEqual(unread_messages_count_new, 0)

    def test_read_list_messages(self):
        first_msg, second_msg = self.room.messages.filter(seen=False)[:2]

        data = {"seen": True, "messages": [str(first_msg.pk), str(second_msg.pk)]}
        response = self._update_message_status(token=self.agent_token, data=data)
        first_msg.refresh_from_db()
        second_msg.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(first_msg.seen and second_msg.seen)

    def test_read_empty_list_messages(self):
        data = {"seen": True, "messages": ["", ""]}
        response = self._update_message_status(token=self.agent_token, data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_read_all_empty_body_messages(self):
        unread_messages_count_old = self.room.messages.filter(seen=False).count()

        response = self._update_message_status(token=self.agent_token, data={})

        unread_messages_count_new = self.room.messages.filter(seen=False).count()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(unread_messages_count_new, unread_messages_count_old)
        self.assertEqual(unread_messages_count_new, 0)

    def test_unread_all_messages(self):
        self.room.messages.update(seen=True)
        read_messages_count_old = self.room.messages.count()

        data = {"seen": False}
        response = self._update_message_status(token=self.agent_token, data=data)

        read_messages_count_new = self.room.messages.filter(seen=True).count()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(read_messages_count_new, read_messages_count_old)
        self.assertEqual(read_messages_count_new, 0)

    def test_unread_list_messages(self):
        self.room.messages.update(seen=True)
        first_msg, second_msg = self.room.messages.all()[:2]

        data = {"seen": False, "messages": [str(first_msg.pk), str(second_msg.pk)]}
        response = self._update_message_status(token=self.agent_token, data=data)
        first_msg.refresh_from_db()
        second_msg.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(first_msg.seen and second_msg.seen)


class RoomsManagerTests(APITestCase):
    """

    TODO Manager can access agents
    [] Room List
    [] Room Read
    [] Room Transfer

    [] Manager/Admin with X rooms
    [] Agent with Y rooms
    [] Given a agent, Manager/Admin should retrieve Y rooms

    Project: 34a93b52-231e-11ed-861d-0242ac120002
    Queue: f2519480-7e58-4fc4-9894-9ab1769e29cf
    Admin: amazoninhaweni@chats.weni.ai <d116bca8757372f3b5936096473929ed1465915e> [0 rooms]
    Manager(in other sector): linalawson@chats.weni.ai <d7fddba0b1dfaad72aa9e21876cbc93caa9ce3fa> [0 rooms]
    Agent_1: amywong@chats.weni.ai <4215e6d6666e54f7db9f98100533aa68909fd855> [2 rooms]
    Agent_2: johndoe@chats.weni.ai <59e5b85e2f0134c4ee9f72037e379c94390697ce> [0 rooms]

    """

    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.admin = User.objects.get(email="amazoninhaweni@chats.weni.ai")
        self.manager = User.objects.get(email="linalawson@chats.weni.ai")
        self.agent_1 = User.objects.get(email="amywong@chats.weni.ai")
        self.agent_2 = User.objects.get(email="johndoe@chats.weni.ai")
        self.room = Room.objects.get(pk="090da6d1-959e-4dea-994a-41bf0d38ba26")

    def _request_list_rooms(self, token, data: dict):
        url = reverse("room-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data=data)
        results = response.json().get("results")
        return response, results

    def _request_transfer_room(self, token, data: dict):
        url = reverse("room-detail", kwargs={"pk": str(self.room.pk)})
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.patch(url, data=data)
        results = response.json().get("results")
        return response, results

    def test_admin_list_agent_rooms(self):
        data = {"project": str(self.project.pk)}
        admin_data = {**data, **{"email": self.agent_1.email}}
        admin_response = self._request_list_rooms(
            self.admin.auth_token.key, admin_data
        )[0]
        agent_response = self._request_list_rooms(self.agent_1.auth_token.key, data)[0]
        admin_content = admin_response.json()
        agent_content = agent_response.json()
        self.assertEquals(admin_response.status_code, status.HTTP_200_OK)
        self.assertEquals(admin_content.get("count"), agent_content.get("count"))

    def test_manager_list_agent_rooms(self):
        data = {"project": str(self.project.pk)}
        manager_data = {**data, **{"email": self.agent_1.email}}
        manager_response = self._request_list_rooms(
            self.manager.auth_token.key, manager_data
        )[0]
        agent_response = self._request_list_rooms(self.agent_1.auth_token.key, data)[0]
        manager_content = manager_response.json()
        agent_content = agent_response.json()
        self.assertEquals(manager_response.status_code, status.HTTP_200_OK)
        self.assertEquals(manager_content.get("count"), agent_content.get("count"))

    def test_admin_transfer_agent_rooms(self):
        data = {"user_email": self.agent_2.email}
        response = self._request_transfer_room(self.admin.auth_token.key, data)[0]
        room = self.room
        room.refresh_from_db()
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(room.user, self.agent_2)

    def test_manager_transfer_agent_rooms(self):
        data = {"user_email": self.agent_2.email}
        response = self._request_transfer_room(self.manager.auth_token.key, data)[0]
        room = self.room
        room.refresh_from_db()
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(room.user, self.agent_2)


class TestRoomsViewSet(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(email="test@test.com")
        self.project = Project.objects.create(name="Test Project")
        self.project_permission = ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.queue_permission = QueueAuthorization.objects.create(
            permission=self.project_permission,
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        self.client.force_authenticate(user=self.user)

    def list_rooms(self, filters: dict = {}) -> Response:
        url = reverse("room-list")

        return self.client.get(url, filters)

    def test_room_order_by_created_on(self):
        room_1 = Room.objects.create(
            project_uuid=str(self.project.uuid),
            is_active=True,
            queue=self.queue,
            contact=Contact.objects.create(),
        )
        room_2 = Room.objects.create(
            project_uuid=str(self.project.uuid),
            is_active=True,
            queue=self.queue,
            contact=Contact.objects.create(),
        )

        response = self.list_rooms(
            filters={"project": str(self.project.uuid), "ordering": "created_on"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json().get("results")[0].get("uuid"), str(room_1.uuid)
        )
        self.assertEqual(
            response.json().get("results")[1].get("uuid"), str(room_2.uuid)
        )

    def test_room_order_by_inverted_created_on(self):
        room_1 = Room.objects.create(
            project_uuid=str(self.project.uuid),
            is_active=True,
            queue=self.queue,
            contact=Contact.objects.create(),
        )
        room_2 = Room.objects.create(
            project_uuid=str(self.project.uuid),
            is_active=True,
            queue=self.queue,
            contact=Contact.objects.create(),
        )

        response = self.list_rooms(
            filters={"project": str(self.project.uuid), "ordering": "-created_on"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json().get("results")[0].get("uuid"), str(room_2.uuid)
        )
        self.assertEqual(
            response.json().get("results")[1].get("uuid"), str(room_1.uuid)
        )

    def test_room_order_with_pin(self):
        # Create rooms
        room_1 = Room.objects.create(queue=self.queue, contact=Contact.objects.create())
        room_2 = Room.objects.create(queue=self.queue, contact=Contact.objects.create())
        room_3 = Room.objects.create(queue=self.queue, contact=Contact.objects.create())
        room_4 = Room.objects.create(queue=self.queue, contact=Contact.objects.create())

        RoomPin.objects.create(room=room_3, user=self.user)
        RoomPin.objects.create(room=room_2, user=self.user)

        queue = Queue.objects.create(
            name="Test Queue",
            sector=Sector.objects.create(
                name="Test Sector",
                project=Project.objects.create(name="Test Project"),
                rooms_limit=10,
                work_start="09:00",
                work_end="18:00",
            ),
        )
        QueueAuthorization.objects.create(
            permission=ProjectPermission.objects.create(
                user=self.user,
                project=queue.sector.project,
                role=ProjectPermission.ROLE_ATTENDANT,
            ),
            queue=queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        # Room from a different project, should be excluded
        room_5 = Room.objects.create(queue=queue, contact=Contact.objects.create())
        RoomPin.objects.create(room=room_5, user=self.user)

        response = self.list_rooms(
            filters={
                "project": str(self.project.uuid),
                "is_active": True,
                "ordering": "-created_on",
            }
        )

        self.assertIn("max_pin_limit", response.data)
        self.assertEqual(
            response.data.get("max_pin_limit"), settings.MAX_ROOM_PINS_LIMIT
        )

        results = response.data.get("results")
        rooms_uuids = [room["uuid"] for room in results]

        self.assertNotIn(str(room_5.uuid), rooms_uuids)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(rooms_uuids[0], str(room_2.uuid))
        self.assertEqual(results[0].get("is_pinned"), True)

        self.assertEqual(rooms_uuids[1], str(room_3.uuid))
        self.assertEqual(results[1].get("is_pinned"), True)

        self.assertEqual(rooms_uuids[2], str(room_4.uuid))
        self.assertEqual(results[2].get("is_pinned"), False)

        self.assertEqual(rooms_uuids[3], str(room_1.uuid))
        self.assertEqual(results[3].get("is_pinned"), False)

    def test_room_order_with_email(self):
        another_user = User.objects.create(email="another_user@example.com")
        QueueAuthorization.objects.create(
            permission=ProjectPermission.objects.create(
                user=another_user,
                project=self.project,
                role=ProjectPermission.ROLE_ADMIN,
            ),
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

        rooms = []

        for i in range(3):
            room = Room.objects.create(
                queue=self.queue, contact=Contact.objects.create(), user=another_user
            )
            rooms.append(room)

        RoomPin.objects.create(room=rooms[1], user=another_user)

        response = self.list_rooms(
            filters={
                "project": str(self.project.uuid),
                "is_active": True,
                "ordering": "-created_on",
                "email": another_user.email,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data.get("results")

        self.assertEqual(results[0]["uuid"], str(rooms[1].uuid))
        self.assertEqual(results[0].get("is_pinned"), True)
        self.assertEqual(results[1]["uuid"], str(rooms[2].uuid))
        self.assertEqual(results[1].get("is_pinned"), False)
        self.assertEqual(results[2]["uuid"], str(rooms[0].uuid))
        self.assertEqual(results[2].get("is_pinned"), False)


class RoomPickTests(APITestCase):
    def setUp(self) -> None:
        self.project = Project.objects.create()
        self.sector = Sector.objects.create(
            project=self.project, rooms_limit=10, work_start="05:00", work_end="23:00"
        )
        self.queue = Queue.objects.create(sector=self.sector)
        self.room = Room.objects.create(queue=self.queue)

        self.user = User.objects.create(email="test@example.com")

        self.client.force_authenticate(user=self.user)

    def pick_room_from_queue(self) -> Response:
        url = reverse("room-pick_queue_room", kwargs={"pk": str(self.room.pk)})

        return self.client.patch(url)

    def test_cannot_pick_room_from_queue_without_project_permission(self):
        response = self.pick_room_from_queue()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"].code, "permission_denied")

    @with_project_permission(role=ProjectPermission.ROLE_ADMIN)
    def test_cannot_pick_room_if_room_is_not_queued(self):
        self.room.user = User.objects.create(email="test2@example.com")
        self.room.save(update_fields=["user"])

        response = self.pick_room_from_queue()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"].code, "room_is_not_queued")

    @with_project_permission(role=ProjectPermission.ROLE_ADMIN)
    def test_can_pick_room_if_room_is_queued_as_admin(self):
        self.room.queue = self.queue
        self.room.save()

        response = self.pick_room_from_queue()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    def test_cannot_pick_room_as_attendant_without_queue_authorization(self):
        self.room.queue = self.queue
        self.room.save()

        response = self.pick_room_from_queue()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"].code, "permission_denied")

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    @with_queue_authorization(role=QueueAuthorization.ROLE_AGENT)
    def test_can_pick_room_as_attendant_with_queue_authorization(self):
        self.room.queue = self.queue
        self.room.save()

        response = self.pick_room_from_queue()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @with_project_permission(role=ProjectPermission.ROLE_ADMIN)
    def test_can_pick_room_if_project_routing_type_is_queue_priority_and_user_is_project_admin(
        self,
    ):
        self.project.room_routing_type = RoomRoutingType.QUEUE_PRIORITY
        self.project.save(update_fields=["room_routing_type"])

        response = self.pick_room_from_queue()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @with_project_permission(role=ProjectPermission.ROLE_ATTENDANT)
    @with_sector_authorization(role=SectorAuthorization.ROLE_MANAGER)
    def test_can_pick_room_if_project_routing_type_is_queue_priority_and_user_has_sector_manager_role(
        self,
    ):
        self.project.room_routing_type = RoomRoutingType.QUEUE_PRIORITY
        self.project.save(update_fields=["room_routing_type"])

        response = self.pick_room_from_queue()

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RoomsBulkTransferTestCase(APITestCase):
    def setUp(self) -> None:
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )

        self.agent_1 = User.objects.create(
            email="test_agent_1@example.com",
        )
        self.agent_2 = User.objects.create(
            email="test_agent_2@example.com",
        )

        for agent in [self.agent_1, self.agent_2]:
            perm = ProjectPermission.objects.create(
                project=self.project,
                user=agent,
                role=ProjectPermission.ROLE_ADMIN,
                status="ONLINE",
            )
            QueueAuthorization.objects.create(
                queue=self.queue,
                permission=perm,
                role=QueueAuthorization.ROLE_AGENT,
            )

        self.room = Room.objects.create(
            queue=self.queue,
            user=self.agent_1,
        )

        self.client.force_authenticate(user=self.agent_1)

    @patch("chats.apps.api.v1.rooms.viewsets.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.viewsets.logger")
    def test_bulk_transfer_to_user(
        self, mock_logger, mock_start_queue_priority_routing
    ):
        mock_start_queue_priority_routing.return_value = None

        url = reverse("room-bulk_transfer")

        response = self.client.patch(
            url,
            data={
                "rooms_list": [self.room.uuid],
            },
            format="json",
            QUERY_STRING=f"user_email={self.agent_2.email}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_start_queue_priority_routing.assert_called_once()
        mock_logger.info.assert_called_once_with(
            "Starting queue priority routing for room %s from bulk transfer to user %s",
            self.room.uuid,
            self.agent_2.email,
        )

    @patch("chats.apps.api.v1.rooms.viewsets.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.viewsets.logger")
    def test_bulk_transfer_to_queue(
        self, mock_logger, mock_start_queue_priority_routing
    ):
        mock_start_queue_priority_routing.return_value = None

        url = reverse("room-bulk_transfer")

        new_queue = Queue.objects.create(
            name="New Queue",
            sector=self.sector,
        )

        response = self.client.patch(
            url,
            data={
                "rooms_list": [self.room.uuid],
            },
            format="json",
            QUERY_STRING=f"queue_uuid={new_queue.uuid}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_start_queue_priority_routing.assert_called_once()
        mock_logger.info.assert_called_once_with(
            "Starting queue priority routing for room %s from bulk transfer to queue %s",
            self.room.uuid,
            new_queue.uuid,
        )

    def test_cannot_transfer_rooms_from_another_project(self):
        p = Project.objects.create(
            name="Another Project",
        )
        self.sector.project = p
        self.sector.save()

        response = self.client.patch(
            reverse("room-bulk_transfer"),
            data={
                "rooms_list": [self.room.uuid],
            },
            format="json",
            QUERY_STRING=f"user_email={self.agent_2.email}",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            f"User {self.agent_2.email} has no permission on the project {p.name} <{p.uuid}>",
        )


class CloseRoomTestCase(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.agent = User.objects.create(
            email="test_agent_1@example.com",
        )

        perm = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ADMIN,
            status="ONLINE",
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=perm,
            role=QueueAuthorization.ROLE_AGENT,
        )

        self.room = Room.objects.create(
            queue=self.queue, user=self.agent, config={"is_billing_notified": True}
        )

        self.client.force_authenticate(user=self.agent)

    def close_room(self, room_pk: str, payload: dict = None) -> Response:
        url = reverse("room-close", kwargs={"pk": room_pk})

        return self.client.patch(url, data=payload, format="json")

    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_close_room_when_billing_was_not_previously_notified(self, mock_get_room):
        mock_get_room.return_value = None
        self.room.set_config("is_billing_notified", False)
        self.room.save(update_fields=["config"])

        self.assertFalse(self.room.is_billing_notified)

        response = self.close_room(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.room.refresh_from_db()
        self.assertEqual(self.room.is_active, False)
        mock_get_room.assert_called_once_with(self.room)
        self.assertTrue(self.room.is_billing_notified)

    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_close_room_when_billing_was_previously_notified(self, mock_get_room):
        mock_get_room.return_value = None

        self.assertTrue(self.room.is_billing_notified)

        response = self.close_room(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.room.refresh_from_db()
        self.assertEqual(self.room.is_active, False)

        mock_get_room.assert_not_called()

    def test_close_room_when_sector_has_required_tags_and_no_tags_are_provided(self):
        self.sector.required_tags = True
        self.sector.save()

        response = self.close_room(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["tags"][0].code, "tags_required")

    def test_close_room_when_sector_has_required_tags_and_room_already_has_tags(self):
        self.sector.required_tags = True
        self.sector.save()
        self.room.tags.add(
            SectorTag.objects.create(name="Test Tag", sector=self.sector)
        )

        response = self.close_room(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual(self.room.is_active, False)

    def test_close_room_when_sector_has_required_tags_and_tags_are_provided(self):
        self.sector.required_tags = True
        self.sector.save()

        tag = SectorTag.objects.create(name="Test Tag", sector=self.sector)

        response = self.close_room(self.room.uuid, payload={"tags": [tag.uuid]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.room.refresh_from_db()
        self.assertEqual(self.room.is_active, False)


class RoomHistorySummaryTestCase(APITestCase):
    def setUp(self) -> None:
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.room = Room.objects.create(
            queue=self.queue,
        )
        self.user = User.objects.create(
            email="test_user@example.com",
        )

        self.project.permissions.create(
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

        self.client.force_authenticate(user=self.user)

    def get_room_history_summary(self, room_pk: str) -> Response:
        url = reverse("room-chats-summary", kwargs={"pk": room_pk})

        return self.client.get(url)

    def post_room_history_summary_feedback(self, room_pk: str, data: dict) -> Response:
        url = reverse("room-chats-summary-feedback", kwargs={"pk": room_pk})

        return self.client.post(url, data=data, format="json")

    def create_history_summary(
        self,
        room: Room,
        history_summary_status: HistorySummaryStatus = HistorySummaryStatus.DONE,
    ) -> HistorySummary:
        return HistorySummary.objects.create(
            room=room,
            status=history_summary_status,
            summary="Test summary",
        )

    def test_get_room_history_summary_when_no_summary_exists(self):
        response = self.get_room_history_summary(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], HistorySummaryStatus.UNAVAILABLE)
        self.assertEqual(response.data["summary"], None)
        self.assertEqual(response.data["feedback"], {"liked": None})

    def test_get_room_history_summary_when_summary_exists(self):
        history_summary = self.create_history_summary(self.room)

        response = self.get_room_history_summary(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], history_summary.status)
        self.assertEqual(response.data["summary"], history_summary.summary)
        self.assertEqual(response.data["feedback"], {"liked": None})

    def test_get_room_history_summary_when_feedback_exists_and_liked_is_true(self):
        history_summary = self.create_history_summary(self.room)
        history_summary.feedbacks.create(
            user=self.user,
            liked=True,
        )

        response = self.get_room_history_summary(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], history_summary.status)
        self.assertEqual(response.data["summary"], history_summary.summary)
        self.assertEqual(response.data["feedback"], {"liked": True})

    def test_get_room_history_summary_when_feedback_exists_and_liked_is_false(self):
        history_summary = self.create_history_summary(self.room)
        history_summary.feedbacks.create(
            user=self.user,
            liked=False,
        )

        response = self.get_room_history_summary(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], history_summary.status)
        self.assertEqual(response.data["summary"], history_summary.summary)
        self.assertEqual(response.data["feedback"], {"liked": False})

    def test_get_room_history_summary_when_feedback_from_another_user_exists(self):
        history_summary = self.create_history_summary(self.room)
        history_summary.feedbacks.create(
            user=User.objects.create(email="test_user_2@example.com"),
            liked=True,
        )

        response = self.get_room_history_summary(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], history_summary.status)
        self.assertEqual(response.data["summary"], history_summary.summary)
        self.assertEqual(response.data["feedback"], {"liked": None})

    @with_room_user
    def test_post_room_history_summary_feedback_with_liked_as_true(self):
        history_summary = self.create_history_summary(self.room)

        self.assertFalse(history_summary.feedbacks.filter(user=self.user).exists())

        response = self.post_room_history_summary_feedback(
            self.room.uuid, {"liked": True}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["liked"], True)

        self.assertTrue(history_summary.feedbacks.filter(user=self.user).exists())
        feedback = history_summary.feedbacks.filter(user=self.user).first()

        self.assertEqual(feedback.liked, True)
        self.assertEqual(feedback.text, None)

    @with_room_user
    def test_post_room_history_summary_feedback_with_liked_as_false(self):
        history_summary = self.create_history_summary(self.room)

        self.assertFalse(history_summary.feedbacks.filter(user=self.user).exists())

        response = self.post_room_history_summary_feedback(
            self.room.uuid, {"liked": False}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["liked"], False)

        self.assertTrue(history_summary.feedbacks.filter(user=self.user).exists())
        feedback = history_summary.feedbacks.filter(user=self.user).first()

        self.assertEqual(feedback.liked, False)
        self.assertEqual(feedback.text, None)

    @with_room_user
    def test_post_room_history_summary_feedback_with_text(self):
        history_summary = self.create_history_summary(self.room)

        self.assertFalse(history_summary.feedbacks.filter(user=self.user).exists())

        response = self.post_room_history_summary_feedback(
            self.room.uuid, {"liked": True, "text": "Test feedback"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["liked"], True)
        self.assertEqual(response.data["text"], "Test feedback")

        self.assertTrue(history_summary.feedbacks.filter(user=self.user).exists())
        feedback = history_summary.feedbacks.filter(user=self.user).first()

        self.assertEqual(feedback.liked, True)
        self.assertEqual(feedback.text, "Test feedback")

    @with_room_user
    def test_post_room_history_summary_feedback_when_the_room_does_not_exist(self):
        response = self.post_room_history_summary_feedback(
            uuid.uuid4(), {"liked": True}
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @with_room_user
    def test_post_room_history_summary_feedback_when_the_history_summary_does_not_exist(
        self,
    ):
        response = self.post_room_history_summary_feedback(
            self.room.uuid, {"liked": True}
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_room_history_summary_feedback_when_the_user_is_not_the_room_user(
        self,
    ):
        history_summary = self.create_history_summary(self.room)

        self.assertFalse(history_summary.feedbacks.filter(user=self.user).exists())

        response = self.post_room_history_summary_feedback(
            self.room.uuid, {"liked": True}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"].code, "user_is_not_the_room_user")

        self.assertFalse(history_summary.feedbacks.filter(user=self.user).exists())

    @with_room_user
    def test_post_room_history_summary_feedback_when_user_already_gave_feedback(
        self,
    ):
        history_summary = self.create_history_summary(self.room)
        feedback = history_summary.feedbacks.create(
            user=self.user,
            liked=True,
            text="Test feedback",
        )

        payload = {"liked": False, "text": "Test feedback 2"}
        response = self.post_room_history_summary_feedback(self.room.uuid, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["liked"], payload["liked"])
        self.assertEqual(response.data["text"], payload["text"])

        feedback.refresh_from_db()

        self.assertEqual(feedback.liked, payload["liked"])
        self.assertEqual(feedback.text, payload["text"])

    @with_room_user
    def test_post_room_history_summary_feedback_when_user_already_gave_feedback_without_text(
        self,
    ):
        history_summary = self.create_history_summary(self.room)
        feedback = history_summary.feedbacks.create(
            user=self.user,
            liked=True,
            text="Test feedback",
        )

        payload = {"liked": False}
        response = self.post_room_history_summary_feedback(self.room.uuid, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["liked"], payload["liked"])
        self.assertIsNone(response.data["text"])

        feedback.refresh_from_db()

        self.assertEqual(feedback.liked, payload["liked"])
        self.assertIsNone(feedback.text)

    @with_room_user
    def test_post_room_history_summary_feedback_when_text_exceeds_max_length(
        self,
    ):
        history_summary = self.create_history_summary(self.room)
        self.assertFalse(history_summary.feedbacks.filter(user=self.user).exists())

        response = self.post_room_history_summary_feedback(
            self.room.uuid, {"liked": True, "text": get_random_string(length=151)}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["text"][0].code, "max_length")

        self.assertFalse(history_summary.feedbacks.filter(user=self.user).exists())

    @with_room_user
    def test_post_room_history_summary_feedback_when_history_summary_is_pending(
        self,
    ):
        history_summary = self.create_history_summary(
            self.room, HistorySummaryStatus.PENDING
        )

        response = self.post_room_history_summary_feedback(
            self.room.uuid, {"liked": True}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"].code, "room_history_summary_not_done")

        self.assertFalse(history_summary.feedbacks.filter(user=self.user).exists())

    @with_room_user
    def test_post_room_history_summary_feedback_when_history_summary_is_processing(
        self,
    ):
        history_summary = self.create_history_summary(
            self.room, HistorySummaryStatus.PROCESSING
        )

        response = self.post_room_history_summary_feedback(
            self.room.uuid, {"liked": True}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"].code, "room_history_summary_not_done")

        self.assertFalse(history_summary.feedbacks.filter(user=self.user).exists())

    @with_room_user
    def test_post_room_history_summary_feedback_when_history_summary_is_unavailable(
        self,
    ):
        history_summary = self.create_history_summary(
            self.room, HistorySummaryStatus.UNAVAILABLE
        )

        response = self.post_room_history_summary_feedback(
            self.room.uuid, {"liked": True}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"].code, "room_history_summary_not_done")

        self.assertFalse(history_summary.feedbacks.filter(user=self.user).exists())


class RoomsReportTestCase(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
        )
        self.cache_client = CacheClient()
        self.service = RoomsReportService(self.project)

    def tearDown(self):
        self.cache_client.delete(self.service.get_cache_key())

    def generate_report(self, data: dict) -> Response:
        url = reverse("rooms_report")

        return self.client.post(url, data=data, format="json")

    def test_cannot_generate_report_auth(self):
        response = self.generate_report({})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_generate_report_without_required_fields(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + str(self.project.external_token.uuid)
        )

        response = self.generate_report({})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["recipient_email"][0].code, "required")
        self.assertEqual(response.data["filters"][0].code, "required")

    def test_cannot_generate_report_without_required_filters(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + str(self.project.external_token.uuid)
        )

        body = {
            "recipient_email": "test@example.com",
            "filters": {},
        }

        response = self.generate_report(body)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["filters"]["created_on__gte"][0].code, "required"
        )

    def test_cannot_generate_report_when_report_is_already_generating(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + str(self.project.external_token.uuid)
        )
        self.cache_client.set(self.service.get_cache_key(), "true")

        response = self.generate_report({})

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_cannot_generate_report_when_tags_filter_is_not_a_list(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + str(self.project.external_token.uuid)
        )

        body = {
            "recipient_email": "test@example.com",
            "filters": {
                "created_on__gte": "2021-01-01",
                "created_on__lte": "2021-01-01",
                "tags": "invalid-tags-filter",
            },
        }

        response = self.generate_report(body)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["filters"]["tags"][0].code, "not_a_list")

    def test_cannot_generate_report_with_invalid_tag_in_tags_list(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + str(self.project.external_token.uuid)
        )

        body = {
            "recipient_email": "test@example.com",
            "filters": {
                "created_on__gte": "2021-01-01",
                "created_on__lte": "2021-01-01",
                "tags": ["invalid-tag"],
            },
        }

        response = self.generate_report(body)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["filters"]["tags"][0][0].code, "invalid")

    @patch("chats.apps.api.v1.rooms.viewsets.generate_rooms_report")
    def test_generate_report(self, mock_generate_rooms_report):
        mock_generate_rooms_report.delay.return_value = None
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + str(self.project.external_token.uuid)
        )

        body = {
            "recipient_email": "test@example.com",
            "filters": {
                "created_on__gte": "2021-01-01",
                "created_on__lte": "2021-01-01",
            },
        }

        response = self.generate_report(body)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)


class BaseRoomPinTestCase(APITestCase):
    def pin_room(self, room_pk: str, data: dict) -> Response:
        url = reverse("room-pin", kwargs={"pk": room_pk})

        return self.client.post(url, data=data, format="json")


class TestRoomPinAnonymousUser(BaseRoomPinTestCase):
    def test_cannot_pin_room_when_user_is_not_authenticated(self):
        response = self.pin_room("123", {"status": True})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestRoomPinAuthenticatedUser(BaseRoomPinTestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.agent = User.objects.create(
            email="test_agent_1@example.com",
        )

        self.client.force_authenticate(user=self.agent)

    def test_pin_room(self):
        room = Room.objects.create(
            queue=self.queue,
            user=self.agent,
        )

        response = self.pin_room(room.uuid, {"status": True})

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_pin_room_when_room_is_not_active(self):
        room = Room.objects.create(
            queue=self.queue,
            user=self.agent,
        )
        room.close()
        response = self.pin_room(room.uuid, {"status": True})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "room_is_not_active")

    def test_cannot_pin_room_when_max_pin_limit_reached(self):
        for _ in range(settings.MAX_ROOM_PINS_LIMIT):
            room = Room.objects.create(
                queue=self.queue,
                user=self.agent,
            )
            RoomPin.objects.create(room=room, user=self.agent)

        room = Room.objects.create(
            queue=self.queue,
            user=self.agent,
        )
        response = self.pin_room(room.uuid, {"status": True})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "max_pin_limit")

    def test_cannot_pin_room_when_user_is_not_assigned(self):
        room = Room.objects.create(
            queue=self.queue,
        )
        response = self.pin_room(room.uuid, {"status": True})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unpin_room(self):
        room = Room.objects.create(
            queue=self.queue,
            user=self.agent,
        )
        response = self.pin_room(room.uuid, {"status": False})

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_unpin_room_when_user_is_not_assigned(self):
        room = Room.objects.create(
            queue=self.queue,
        )
        response = self.pin_room(room.uuid, {"status": False})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BaseTestListRoomTags(APITestCase):
    def list_room_tags(self, room_pk: str) -> Response:
        url = reverse("room-tags", kwargs={"pk": room_pk})

        return self.client.get(url)


class TestListRoomTagsAnonymousUser(BaseTestListRoomTags):
    def test_cannot_list_room_tags_when_user_is_not_authenticated(self):
        response = self.list_room_tags(uuid.uuid4())

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestListRoomTagsAuthenticatedUser(BaseTestListRoomTags):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.tags = [
            SectorTag.objects.create(
                name="Test Tag 1",
                sector=self.sector,
            ),
            SectorTag.objects.create(
                name="Test Tag 2",
                sector=self.sector,
            ),
        ]
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.user = User.objects.create(
            email="test_user_1@example.com",
        )
        self.room = Room.objects.create(
            queue=self.queue,
            user=self.user,
        )
        self.room.tags.set(self.tags)
        self.client.force_authenticate(user=self.user)

    def test_list_room_tags_without_permission(self):
        response = self.list_room_tags(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_project_permission(role=ProjectPermission.ROLE_ADMIN)
    @with_queue_authorization(role=QueueAuthorization.ROLE_AGENT)
    def test_list_room_tags_with_permission(self):
        another_room = Room.objects.create(
            queue=self.queue,
            user=self.user,
        )
        tag = SectorTag.objects.create(
            name="Test Tag 3",
            sector=self.sector,
        )
        another_room.tags.add(tag)

        response = self.list_room_tags(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json().get("results"),
            [
                {
                    "uuid": str(self.tags[0].uuid),
                    "name": self.tags[0].name,
                },
                {
                    "uuid": str(self.tags[1].uuid),
                    "name": self.tags[1].name,
                },
            ],
        )


class BaseTestAddRoomTag(APITestCase):
    def add_room_tag(self, room_pk: str, data: dict) -> Response:
        url = reverse("room-add-tag", kwargs={"pk": room_pk})

        return self.client.post(url, data=data, format="json")


class TestAddRoomTagAnonymousUser(BaseTestAddRoomTag):
    def test_cannot_add_room_tag_when_user_is_not_authenticated(self):
        response = self.add_room_tag(uuid.uuid4(), {"uuid": uuid.uuid4()})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestAddRoomTagAuthenticatedUser(BaseTestAddRoomTag):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.user = User.objects.create(
            email="test_user_1@example.com",
        )
        self.tags = [
            SectorTag.objects.create(
                name="Test Tag 1",
                sector=self.sector,
            ),
        ]
        self.room = Room.objects.create(
            queue=self.queue,
            user=self.user,
        )
        self.client.force_authenticate(user=self.user)

    def test_add_room_tag(self):
        response = self.add_room_tag(self.room.uuid, {"uuid": self.tags[0].uuid})

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.room.refresh_from_db()

        self.assertEqual(self.room.tags.first().uuid, self.tags[0].uuid)

    def test_cannot_add_room_tag_when_room_is_not_active(self):
        self.room.is_active = False
        self.room.save()
        response = self.add_room_tag(self.room.uuid, {"uuid": self.tags[0].uuid})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"].code, "room_is_not_active")

    def test_cannot_add_room_tag_when_tag_already_exists(self):
        self.room.tags.add(self.tags[0])
        response = self.add_room_tag(self.room.uuid, {"uuid": self.tags[0].uuid})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["uuid"][0].code, "tag_already_exists")

    def test_cannot_add_room_tag_when_tag_does_not_exist(self):
        response = self.add_room_tag(self.room.uuid, {"uuid": uuid.uuid4()})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["uuid"][0].code, "tag_not_found")

    def test_cannot_add_tag_from_another_sector(self):
        another_sector = Sector.objects.create(
            name="Another Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )

        another_tag = SectorTag.objects.create(
            name="Another Tag",
            sector=another_sector,
        )

        response = self.add_room_tag(self.room.uuid, {"uuid": another_tag.uuid})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["uuid"][0].code, "tag_not_found")

    def test_cannot_add_room_tag_when_user_is_not_the_room_user(self):
        another_user = User.objects.create(
            email="test_user_2@example.com",
        )
        self.room.user = another_user
        self.room.save()

        response = self.add_room_tag(self.room.uuid, {"uuid": self.tags[0].uuid})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BaseTestRemoveRoomTag(APITestCase):
    def remove_room_tag(self, room_pk: str, data: dict) -> Response:
        url = reverse("room-remove-tag", kwargs={"pk": room_pk})

        return self.client.post(url, data=data, format="json")


class TestRemoveRoomTagAnonymousUser(BaseTestRemoveRoomTag):
    def test_cannot_remove_room_tag_when_user_is_not_authenticated(self):
        response = self.remove_room_tag(uuid.uuid4(), {"uuid": uuid.uuid4()})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestRemoveRoomTagAuthenticatedUser(BaseTestRemoveRoomTag):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.user = User.objects.create(
            email="test_user_1@example.com",
        )
        self.tags = [
            SectorTag.objects.create(
                name="Test Tag 1",
                sector=self.sector,
            ),
        ]
        self.room = Room.objects.create(
            queue=self.queue,
            user=self.user,
        )
        self.room.tags.add(self.tags[0])
        self.client.force_authenticate(user=self.user)

    def test_remove_room_tag(self):
        response = self.remove_room_tag(self.room.uuid, {"uuid": self.tags[0].uuid})

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.room.refresh_from_db()

        self.assertEqual(self.room.tags.count(), 0)

    def test_cannot_remove_room_tag_when_room_is_not_active(self):
        self.room.is_active = False
        self.room.save()
        response = self.remove_room_tag(self.room.uuid, {"uuid": self.tags[0].uuid})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"].code, "room_is_not_active")

    def test_cannot_remove_room_tag_when_tag_does_not_exist(self):
        response = self.remove_room_tag(self.room.uuid, {"uuid": uuid.uuid4()})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["uuid"][0].code, "tag_not_found")

    def test_cannot_remove_room_tag_when_user_is_not_the_room_user(self):
        another_user = User.objects.create(
            email="test_user_2@example.com",
        )
        self.room.user = another_user
        self.room.save()

        response = self.remove_room_tag(self.room.uuid, {"uuid": self.tags[0].uuid})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BaseTestCanSendMessageStatus(APITestCase):
    def get_can_send_message_status(self, room_pk: str) -> Response:
        url = reverse("room-can-send-message-status", kwargs={"pk": room_pk})

        return self.client.get(url)


class TestCanSendMessageStatusAnonymousUser(BaseTestCanSendMessageStatus):
    def test_cannot_get_can_send_message_status_when_user_is_not_authenticated(self):
        response = self.get_can_send_message_status(uuid.uuid4())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestCanSendMessageStatusAuthenticatedUser(BaseTestCanSendMessageStatus):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )
        self.user = User.objects.create(
            email="test_user_1@example.com",
        )
        self.room = Room.objects.create(
            queue=self.queue,
            user=self.user,
            urn="whatsapp:1234567890",
        )

        self.client.force_authenticate(user=self.user)

    def test_get_can_send_message_status_without_project_permission(self):
        response = self.get_can_send_message_status(self.room.uuid)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("chats.apps.rooms.models.Room.is_24h_valid", new_callable=PropertyMock)
    @with_project_permission(role=ProjectPermission.ROLE_ADMIN)
    def test_get_can_send_message_status_with_project_permission_when_true(
        self, mock_is_24h_valid
    ):
        mock_is_24h_valid.return_value = True
        response = self.get_can_send_message_status(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["can_send_message"], True)

    @patch("chats.apps.rooms.models.Room.is_24h_valid", new_callable=PropertyMock)
    @with_project_permission(role=ProjectPermission.ROLE_ADMIN)
    def test_get_can_send_message_status_with_project_permission_when_false(
        self, mock_is_24h_valid
    ):
        mock_is_24h_valid.return_value = False
        response = self.get_can_send_message_status(self.room.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["can_send_message"], False)
