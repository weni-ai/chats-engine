from unittest.mock import patch

from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.accounts.tests.decorators import with_internal_auth
from chats.apps.msgs.models import Message
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.contacts.models import Contact


PENDING_RESPONSE_FF_PATH = (
    "chats.apps.api.v1.internal.rooms.viewsets.is_feature_active_for_attributes"
)


class BaseTestInternalProtocolRoomsViewSet(APITestCase):
    def list_protocols(self, filters: dict = {}) -> Response:
        url = "/v1/internal/rooms/protocols/"
        return self.client.get(url, filters)


class TestInternalProtocolRoomsViewSetAsAnonymousUser(
    BaseTestInternalProtocolRoomsViewSet
):
    def test_list_protocols_without_authentication(self):
        response = self.list_protocols()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestInternalProtocolRoomsViewSetAsAuthenticatedUser(
    BaseTestInternalProtocolRoomsViewSet
):
    def setUp(self):
        self.user = User.objects.create_user(email="internal@vtex.com")
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.room_with_protocol = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact", email="test@test.com"),
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
            protocol="test",
        )
        self.room_without_protocol = Room.objects.create(
            contact=Contact.objects.create(name="Test Contact", email="test@test.com"),
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )

        self.client.force_authenticate(self.user)

    def test_list_protocols_without_permission(self):
        response = self.list_protocols()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @with_internal_auth
    def test_list_protocols_with_permission(self):
        response = self.list_protocols({"project": str(self.project.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["protocol"], self.room_with_protocol.protocol
        )


class TestInternalListRoomsPendingResponseField(APITestCase):
    """
    Tests for the `pending_response` field on `GET /v1/internal/rooms/`.

    `pending_response` should be True when the room's `last_message` was sent
    by the contact AND `Room.unread_messages_count == 0` (i.e. the agent has
    already opened the room — `clear_unread_messages_count` was called — but
    hasn't replied yet).

    The field is only returned when the
    `INTERNAL_ROOMS_LIST_PENDING_RESPONSE_FEATURE_FLAG_KEY` feature flag is
    active for the requesting project.
    """

    def setUp(self):
        self.user = User.objects.create_user(email="internal@vtex.com")
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.client.force_authenticate(self.user)

    def _create_room(self, name: str) -> Room:
        contact = Contact.objects.create(name=name, email=f"{name}@test.com")
        return Room.objects.create(
            contact=contact,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )

    def _set_last_contact_message(self, room: Room, unread_count: int = 0) -> Message:
        """Simulates a contact message arriving. `unread_count=0` means the
        agent has already opened the room (clear_unread_messages_count was
        called)."""
        message = Message.objects.create(
            room=room, contact=room.contact, text="hi"
        )
        Room.objects.filter(pk=room.pk).update(
            last_message=message,
            last_message_contact=room.contact,
            last_message_user=None,
            last_message_text=message.text,
            unread_messages_count=unread_count,
        )
        return message

    def _set_last_agent_message(self, room: Room) -> Message:
        message = Message.objects.create(
            room=room, user=self.user, text="hello"
        )
        Room.objects.filter(pk=room.pk).update(
            last_message=message,
            last_message_contact=None,
            last_message_user=self.user,
            last_message_text=message.text,
            unread_messages_count=0,
        )
        return message

    def _list_rooms(self):
        return self.client.get(
            "/v1/internal/rooms/", {"project": str(self.project.uuid)}
        )

    def _result_for(self, response, room: Room) -> dict:
        for item in response.data["results"]:
            if str(item["uuid"]) == str(room.uuid):
                return item
        self.fail(f"Room {room.uuid} not found in response")

    @with_internal_auth
    @patch(PENDING_RESPONSE_FF_PATH, return_value=True)
    def test_pending_response_true_when_last_msg_from_contact_and_unread_zero(
        self, _mock_ff
    ):
        room = self._create_room("Contact Read")
        self._set_last_contact_message(room, unread_count=0)

        response = self._list_rooms()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self._result_for(response, room)["pending_response"])

    @with_internal_auth
    @patch(PENDING_RESPONSE_FF_PATH, return_value=True)
    def test_pending_response_false_when_last_msg_from_contact_with_unread(
        self, _mock_ff
    ):
        room = self._create_room("Contact Unread")
        self._set_last_contact_message(room, unread_count=3)

        response = self._list_rooms()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self._result_for(response, room)["pending_response"])

    @with_internal_auth
    @patch(PENDING_RESPONSE_FF_PATH, return_value=True)
    def test_pending_response_false_when_last_message_from_agent(self, _mock_ff):
        room = self._create_room("Agent Replied")
        self._set_last_agent_message(room)

        response = self._list_rooms()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self._result_for(response, room)["pending_response"])

    @with_internal_auth
    @patch(PENDING_RESPONSE_FF_PATH, return_value=True)
    def test_pending_response_false_when_no_last_message(self, _mock_ff):
        room = self._create_room("No Messages")

        response = self._list_rooms()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self._result_for(response, room)["pending_response"])

    @with_internal_auth
    @patch(PENDING_RESPONSE_FF_PATH, return_value=False)
    def test_pending_response_field_absent_when_feature_flag_disabled(
        self, _mock_ff
    ):
        room = self._create_room("FF Disabled")
        self._set_last_contact_message(room, unread_count=0)

        response = self._list_rooms()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = self._result_for(response, room)
        self.assertNotIn("pending_response", result)

    @with_internal_auth
    def test_pending_response_field_absent_when_feature_flag_errors(self):
        """When the feature flag client raises, treat it as disabled and omit
        the field instead of breaking the response."""
        room = self._create_room("FF Error")
        self._set_last_contact_message(room, unread_count=0)

        with patch(PENDING_RESPONSE_FF_PATH, side_effect=Exception("boom")):
            response = self._list_rooms()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("pending_response", self._result_for(response, room))

    @with_internal_auth
    @patch(PENDING_RESPONSE_FF_PATH, return_value=False)
    def test_list_rooms_with_null_contact_does_not_500(self, _mock_ff):
        """
        Rooms without a contact must serialize with contact="".

        CharField(source="contact.name") raises when contact is None.
        """
        room = Room.objects.create(
            contact=None,
            queue=self.queue,
            user=self.user,
            project_uuid=str(self.project.uuid),
        )

        response = self._list_rooms()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._result_for(response, room)["contact"], "")
