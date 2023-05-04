from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_contact, create_user_and_token
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization

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
            contact=self.contact, queue=self.queue_1, user=self.agent
        )
        self.room_2 = Room.objects.create(contact=self.contact_2, queue=self.queue_2)
        self.room_3 = Room.objects.create(contact=self.contact_3, queue=self.queue_3)

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
