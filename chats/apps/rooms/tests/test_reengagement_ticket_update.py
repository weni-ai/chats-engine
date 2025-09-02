# chats/apps/rooms/tests/test_reengagement_ticket_update.py
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.rooms.models import Room
from chats.apps.queues.models import Queue


class RoomsFlowStartReengagementTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        # Reaproveita a mesma estrutura usada em RoomsFlowStartExternalTests
        self.queue: Queue = Queue.objects.get(uuid="f2519480-7e58-4fc4-9894-9ab1769e29cf")
        self.project = self.queue.sector.project
        # Pega uma sala ativa já existente (com usuário) para simular o reengajamento
        self.room: Room = self.queue.rooms.filter(is_active=True, user__isnull=False).first()
        
        # CRIA TOKEN EXTERNO (ProjectPermission com user=None)
        external_token = self.project.permissions.create(user=None, role=1)
        
        self.flow_start = self.project.flowstarts.create(
            flow="a75d0853-e4e8-48bd-bdb5-f8685a0d5026",
            permission=self.project.permissions.get(user=self.room.user),
            room=self.room,
        )
        # Vincula o flowstart ao mesmo contato da sala (caminho get_active_room_flow_start)
        self.flow_start.references.create(
            receiver_type="contact", external_id=str(self.room.contact.external_id)
        )

        # Garante que haverá update (estado inicial sem ticket e sem callback)
        self.room.ticket_uuid = None
        self.room.callback_url = None
        self.room.save(update_fields=["ticket_uuid", "callback_url"])

        self.url = reverse("external_rooms-list")
        self.auth = f"Bearer {external_token.uuid}"

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    @patch("chats.apps.rooms.models.Room.request_callback")
    def test_reengagement_updates_ticket_and_callback_and_calls_callback(
        self, mock_request_callback, mock_get_room, mock_is_attending
    ):
        # Mock para retornar a sala existente (simula reengajamento)
        mock_get_room.return_value = None

        payload = {
            "queue_uuid": str(self.queue.uuid),
            "contact": {
                "external_id": str(self.room.contact.external_id),
                "name": "John Doe",
                "urn": "whatsapp:5521917078236?auth=token",
            },
            "flow_uuid": self.flow_start.flow,
            "ticket_uuid": "11111111-2222-3333-4444-555555555555",
            "callback_url": "https://example.com/hook",
        }

        client = self.client
        client.credentials(HTTP_AUTHORIZATION=self.auth)
        resp = client.post(self.url, data=payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # Deve devolver a mesma sala (reaproveitada)
        self.assertEqual(resp.json().get("uuid"), str(self.room.pk))

        # Atualizações aplicadas
        self.room.refresh_from_db()
        self.assertEqual(str(self.room.ticket_uuid), payload["ticket_uuid"])
        self.assertEqual(self.room.callback_url, payload["callback_url"])

        # Callback chamado após atualizar os campos (caminho com update_fields)
        mock_request_callback.assert_called_once()

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    @patch("chats.apps.rooms.models.Room.request_callback")
    @patch("chats.apps.api.v1.external.rooms.serializers.get_active_room_flow_start")
    def test_reengagement_without_update_fields_does_not_call_callback(
        self, mock_get_active_room, mock_request_callback, mock_get_room, mock_is_attending
    ):
        # Mock para retornar a sala existente (simula reengajamento)
        mock_get_active_room.return_value = self.room
        mock_get_room.return_value = None

        # Sem ticket_uuid e sem callback_url => não deve chamar callback
        payload = {
            "queue_uuid": str(self.queue.uuid),
            "contact": {
                "external_id": str(self.room.contact.external_id),
                "name": "John Doe",
                "urn": "whatsapp:5521917078236?auth=token",
            },
            "flow_uuid": self.flow_start.flow,
        }

        client = self.client
        client.credentials(HTTP_AUTHORIZATION=self.auth)
        resp = client.post(self.url, data=payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.json().get("uuid"), str(self.room.pk))

        self.room.refresh_from_db()
        # Como não mandamos novos valores, continuam None
        self.assertIsNone(self.room.ticket_uuid)
        self.assertIsNone(self.room.callback_url)

        # Sem update_fields => sem callback
        mock_request_callback.assert_not_called()
