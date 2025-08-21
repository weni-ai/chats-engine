from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from chats.apps.projects.models.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue


class ExternalRoomsWorkingHoursTests(APITestCase):
    def setUp(self) -> None:
        self.project = Project.objects.create(name="proj", timezone="America/Sao_Paulo")
        self.sector = Sector.objects.create(
            project=self.project,
            rooms_limit=1,
            open_offline=True,
            working_day={
                "working_hours": {
                    "schedules": {
                        "monday": [{"start": "08:00", "end": "18:00"}],
                        "tuesday": [{"start": "08:00", "end": "18:00"}],
                        "wednesday": [{"start": "08:00", "end": "18:00"}],
                        "thursday": [{"start": "08:00", "end": "18:00"}],
                        "friday": [{"start": "08:00", "end": "18:00"}],
                        "saturday": None,
                        "sunday": None,
                    }
                }
            },
        )
        self.queue = Queue.objects.create(sector=self.sector)
        self.token = str(self.project.external_token.uuid)

    def _create(self, payload: dict):
        url = reverse("external_rooms-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        return self.client.post(url, data=payload, format="json")

    def _base_payload(self) -> dict:
        return {
            "ticket_uuid": "12345678-1234-1234-1234-123456789abc",
            "queue_uuid": str(self.queue.uuid),
            "sector_uuid": str(self.sector.uuid),
            "contact": {
                "external_id": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
                "name": "Foo Bar",
                "email": "alan.dovale@weni.ai",
                "phone": "+250788123123",
                "urn": "tel:+250788123123",
                "custom_fields": {"age": 30, "preferences": "chat"},
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}],
            },
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "protocol": "1234567890",
        }

    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room", return_value=None)
    def test_denies_outside_working_hours_weekday(self, _mock_billing):
        # Quinta-feira 2025-08-21 20:00 -03:00 (fora do intervalo 08:00–18:00)
        payload = self._base_payload()
        payload["contact"]["external_id"] = "00000000-0000-0000-0000-000000000001"
        payload["created_on"] = "2025-08-21T20:00:00-03:00"
        resp = self._create(payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room", return_value=None)
    def test_allows_inside_working_hours_weekday(self, _mock_billing):
        # Quinta-feira 2025-08-21 10:00 -03:00 (dentro do horário)
        payload = self._base_payload()
        payload["contact"]["external_id"] = "00000000-0000-0000-0000-000000000002"
        payload["created_on"] = "2025-08-21T10:00:00-03:00"
        resp = self._create(payload)
        print("print do teste", resp.data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room", return_value=None)
    def test_end_time_is_exclusive(self, _mock_billing):
        # Quinta-feira 2025-08-21 18:00 -03:00 (fim do intervalo — deve bloquear)
        payload = self._base_payload()
        payload["contact"]["external_id"] = "00000000-0000-0000-0000-000000000003"
        payload["created_on"] = "2025-08-21T18:00:00-03:00"
        resp = self._create(payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room", return_value=None)
    def test_weekend_without_open_flag_denies(self, _mock_billing):
        # Sábado 2025-08-23 10:00 -03:00 (sem open_in_weekends — deve bloquear)
        payload = self._base_payload()
        payload["contact"]["external_id"] = "00000000-0000-0000-0000-000000000004"
        payload["created_on"] = "2025-08-23T10:00:00-03:00"
        resp = self._create(payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room", return_value=None)
    def test_sector_queue_mismatch_returns_400(self, _mock_billing):
        # sector_uuid diferente do setor da queue -> deve 400
        other_sector = Sector.objects.create(project=self.project, rooms_limit=1)
        payload = self._base_payload()
        payload["contact"]["external_id"] = "00000000-0000-0000-0000-000000000005"
        payload["sector_uuid"] = str(other_sector.uuid)
        payload["created_on"] = "2025-08-21T10:00:00-03:00"
        resp = self._create(payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
