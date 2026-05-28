from django.test import TestCase
from rest_framework.test import APIClient

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room


class TestRoomHistoryEndpoint(TestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self):
        self.client = APIClient()

        self.contact = Contact.objects.create(
            name="Test Contact", external_id="test-external-id"
        )
        self.queue = Queue.objects.first()
        self.project = self.queue.sector.project
        self.room = Room.objects.create(
            project_uuid=str(self.project.uuid),
            queue=self.queue,
            contact=self.contact,
            is_active=True,
        )
        self.base_message = {
            "text": "test message",
            "direction": "incoming",
            "attachments": [],
            "created_on": "2025-03-24T20:22:52.067586Z",
        }
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )

    def test_create_history_success(self):
        """Testa a criação básica do histórico de mensagens"""
        messages_data = [
            self.base_message,
            {
                "text": "resposta",
                "direction": "outgoing",
                "attachments": [],
                "created_on": "2025-03-24T20:22:56.428391Z",
            },
        ]

        response = self.client.post(
            f"/v1/external/rooms/{self.room.pk}/history/",
            data=messages_data,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        messages = Message.objects.filter(room=self.room)
        self.assertEqual(messages.count(), 2)

        created_ons = set(msg.created_on.isoformat() for msg in messages)
        self.assertEqual(
            created_ons,
            {"2025-03-24T20:22:52.067586+00:00", "2025-03-24T20:22:56.428391+00:00"},
        )

        message_texts = {msg.text: msg.created_on.isoformat() for msg in messages}
        self.assertEqual(
            message_texts["test message"], "2025-03-24T20:22:52.067586+00:00"
        )
        self.assertEqual(message_texts["resposta"], "2025-03-24T20:22:56.428391+00:00")

    def test_create_history_with_attachments(self):
        """Testa a criação de histórico com anexos"""
        messages_data = [
            {
                "text": "mensagem com anexo",
                "direction": "incoming",
                "attachments": [
                    {
                        "content_type": "image/jpeg",
                        "url": "https://example.com/image.jpg",
                    }
                ],
                "created_on": "2025-03-24T20:22:52.067586Z",
            }
        ]

        response = self.client.post(
            f"/v1/external/rooms/{self.room.pk}/history/",
            data=messages_data,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        message = Message.objects.filter(room=self.room).first()
        self.assertIsNotNone(message)
        self.assertEqual(message.text, "mensagem com anexo")
        self.assertEqual(
            message.created_on.isoformat(), "2025-03-24T20:22:52.067586+00:00"
        )

        media = MessageMedia.objects.filter(message=message).first()
        self.assertEqual(media.content_type, "image/jpeg")
        self.assertEqual(media.media_url, "https://example.com/image.jpg")
        self.assertEqual(media.message, message)

    def test_create_history_multiple_messages(self):
        """Testa a criação de múltiplas mensagens com created_on diferentes"""
        messages_data = [
            {
                "text": "mensagem 2",
                "direction": "incoming",
                "attachments": [],
                "created_on": "2025-03-24T20:22:56.428391Z",
            },
            {
                "text": "mensagem 1",
                "direction": "incoming",
                "attachments": [],
                "created_on": "2025-03-24T20:22:52.067586Z",
            },
        ]

        response = self.client.post(
            f"/v1/external/rooms/{self.room.pk}/history/",
            data=messages_data,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        messages = Message.objects.filter(room=self.room)
        created_ons = {msg.created_on.isoformat() for msg in messages}
        self.assertEqual(
            created_ons,
            {"2025-03-24T20:22:52.067586+00:00", "2025-03-24T20:22:56.428391+00:00"},
        )

    def test_create_history_wrong_project(self):
        """Testa tentativa de acesso com projeto errado"""
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer 5e2add2a-30c3-499e-b9c4-15be8107130e"
        )

        response = self.client.post(
            f"/v1/external/rooms/{self.room.pk}/history/",
            data=[self.base_message],
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Message.objects.filter(room=self.room).count(), 0)

    def test_create_history_room_not_found(self):
        """Testa tentativa de criar histórico em sala inexistente"""
        fake_id = 999999

        response = self.client.post(
            f"/v1/external/rooms/{fake_id}/history/",
            data=[self.base_message],
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Message.objects.filter(room=self.room).count(), 0)

    def test_create_history_invalid_data(self):
        """Testa validação de dados inválidos - mensagem sem texto e sem anexos"""
        invalid_data = [
            {
                "direction": "incoming",
                "text": None,
                "attachments": [],
                "created_on": "2025-03-24T20:22:52.067586Z",
            }
        ]

        response = self.client.post(
            f"/v1/external/rooms/{self.room.pk}/history/",
            data=invalid_data,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.filter(room=self.room).count(), 0)

    def test_create_history_triggers_default_message(self):
        """Testa se mensagens de entrada disparam mensagem padrão quando apropriado"""
        self.room.user = None
        self.room.save()

        messages_data = [
            {
                "text": "mensagem do cliente",
                "direction": "incoming",
                "attachments": [],
                "created_on": "2025-03-24T20:22:52.067586Z",
            }
        ]

        response = self.client.post(
            f"/v1/external/rooms/{self.room.pk}/history/",
            data=messages_data,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Message.objects.filter(room=self.room).count(), 1)

        message = Message.objects.filter(room=self.room).first()
        self.assertEqual(
            message.created_on.isoformat(), "2025-03-24T20:22:52.067586+00:00"
        )
