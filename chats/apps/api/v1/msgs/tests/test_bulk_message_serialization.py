from django.contrib.auth import get_user_model
from django.test import TestCase

from chats.apps.api.v1.msgs.serializers import (
    MessageSerializer,
    MessageWSSerializer,
    get_message_bulk_message_data,
)
from chats.apps.api.v2.msgs.serializers import MessageSerializerV2
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import (
    BulkMessageSend,
    BulkMessageSendMessage,
    BulkMessageSendMessageStatus,
    BulkMessageSendStatus,
    Message,
)
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


class BulkMessageSerializationTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            email="requester@test.com",
            password="testpass123",
            first_name="Requester",
            last_name="User",
        )
        self.agent = User.objects.create_user(
            email="agent@test.com",
            password="testpass123",
            first_name="Agent",
            last_name="User",
        )
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.room = Room.objects.create(
            contact=Contact.objects.create(name="Contact"),
            queue=self.queue,
            user=self.agent,
            is_active=True,
        )
        self.bulk_send = BulkMessageSend.objects.create(
            user=self.requester,
            project=self.project,
            text="Bulk hello",
            filter_snapshot={},
            status=BulkMessageSendStatus.FINISHED,
        )

    def _create_message(self, text="Hello"):
        return Message.objects.create(
            room=self.room,
            user=self.agent,
            text=text,
        )

    def _link_bulk_message(self, message):
        return BulkMessageSendMessage.objects.create(
            bulk_message_send=self.bulk_send,
            room=self.room,
            message=message,
            status=BulkMessageSendMessageStatus.SUCCESS,
        )

    def test_helper_returns_none_for_non_bulk_message(self):
        message = self._create_message()

        self.assertIsNone(get_message_bulk_message_data(message))

    def test_helper_returns_sent_by_for_bulk_message(self):
        message = self._create_message()
        self._link_bulk_message(message)

        self.assertEqual(
            get_message_bulk_message_data(message),
            {
                "sent_by": {
                    "email": "requester@test.com",
                    "name": "Requester User",
                }
            },
        )

    def test_v1_serializer_bulk_message_null(self):
        message = self._create_message()
        data = MessageSerializer(message).data

        self.assertIsNone(data["bulk_message"])

    def test_v1_serializer_bulk_message_sent_by(self):
        message = self._create_message()
        self._link_bulk_message(message)
        data = MessageSerializer(message).data

        self.assertEqual(
            data["bulk_message"],
            {
                "sent_by": {
                    "email": "requester@test.com",
                    "name": "Requester User",
                }
            },
        )

    def test_v2_serializer_bulk_message_null(self):
        message = self._create_message()
        data = MessageSerializerV2(message).data

        self.assertIsNone(data["bulk_message"])

    def test_v2_serializer_bulk_message_sent_by(self):
        message = self._create_message()
        self._link_bulk_message(message)
        data = MessageSerializerV2(message).data

        self.assertEqual(
            data["bulk_message"],
            {
                "sent_by": {
                    "email": "requester@test.com",
                    "name": "Requester User",
                }
            },
        )

    def test_ws_serializer_includes_bulk_message(self):
        message = self._create_message()
        self._link_bulk_message(message)
        data = MessageWSSerializer(message).data

        self.assertEqual(
            data["bulk_message"],
            {
                "sent_by": {
                    "email": "requester@test.com",
                    "name": "Requester User",
                }
            },
        )

    def test_serialized_ws_data_includes_bulk_message(self):
        message = self._create_message()
        self._link_bulk_message(message)

        self.assertEqual(
            message.serialized_ws_data["bulk_message"],
            {
                "sent_by": {
                    "email": "requester@test.com",
                    "name": "Requester User",
                }
            },
        )
