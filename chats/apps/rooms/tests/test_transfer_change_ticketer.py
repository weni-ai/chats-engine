"""
Integration tests for the change_ticketer Flows side-effect triggered by
room transfer endpoints (PATCH /v1/room/{uuid}/ and POST /v1/room/bulk_transfer/).
"""

import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.contacts.models import Contact
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.exceptions import (
    FlowsChangeTicketerError,
    FlowsTicketerNotFoundError,
)
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


User = get_user_model()


CHANGE_TICKETER_VIEWSETS_PATH = (
    "chats.apps.api.v1.rooms.viewsets.change_ticketer_for_room"
)
CHANGE_TICKETER_BULK_PATH = (
    "chats.apps.api.v1.rooms.services.bulk_transfer_service."
    "change_ticketer_for_room"
)


class _BaseTransferSetup(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@test.com")
        self.agent = User.objects.create_user(email="agent@test.com")
        self.contact = Contact.objects.create(name="Contact")

        self.project = Project.objects.create(name="P")

        ProjectPermission.objects.create(
            user=self.admin,
            project=self.project,
            role=ProjectPermission.ROLE_ADMIN,
        )
        agent_permission = ProjectPermission.objects.create(
            user=self.agent,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.sector_a = Sector.objects.create(
            name="A",
            project=self.project,
            rooms_limit=5,
            work_start="00:00",
            work_end="23:59",
        )
        self.sector_b = Sector.objects.create(
            name="B",
            project=self.project,
            rooms_limit=5,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue_a = Queue.objects.create(name="Q-A", sector=self.sector_a)
        self.queue_b = Queue.objects.create(name="Q-B", sector=self.sector_b)
        self.queue_a2 = Queue.objects.create(
            name="Q-A2", sector=self.sector_a
        )

        QueueAuthorization.objects.create(
            permission=agent_permission,
            queue=self.queue_a,
            role=QueueAuthorization.ROLE_AGENT,
        )
        QueueAuthorization.objects.create(
            permission=agent_permission,
            queue=self.queue_b,
            role=QueueAuthorization.ROLE_AGENT,
        )

        self.room = Room.objects.create(
            queue=self.queue_a,
            contact=self.contact,
            user=self.agent,
            ticket_uuid=uuid.uuid4(),
            is_active=True,
        )

        self.client.force_authenticate(user=self.admin)


@override_settings(USE_WENI_FLOWS=True)
class PatchRoomChangeTicketerTests(_BaseTransferSetup):
    def _patch_room(self, data):
        url = reverse("room-detail", kwargs={"pk": str(self.room.pk)})
        return self.client.patch(url, data=data, format="json")

    @patch(CHANGE_TICKETER_VIEWSETS_PATH)
    def test_change_ticketer_called_when_sector_changes(self, mock_change):
        response = self._patch_room({"queue_uuid": str(self.queue_b.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_change.assert_called_once()
        room_arg, sector_arg = mock_change.call_args.args
        self.assertEqual(room_arg.pk, self.room.pk)
        self.assertEqual(sector_arg, str(self.sector_b.uuid))

        self.room.refresh_from_db()
        self.assertEqual(self.room.queue, self.queue_b)

    @patch(CHANGE_TICKETER_VIEWSETS_PATH)
    def test_change_ticketer_not_called_when_same_sector(self, mock_change):
        response = self._patch_room({"queue_uuid": str(self.queue_a2.uuid)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_change.assert_not_called()

        self.room.refresh_from_db()
        self.assertEqual(self.room.queue, self.queue_a2)

    @patch(CHANGE_TICKETER_VIEWSETS_PATH)
    def test_change_ticketer_not_called_for_user_only_transfer(
        self, mock_change
    ):
        response = self._patch_room({"user_email": "agent@test.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_change.assert_not_called()

    @patch(CHANGE_TICKETER_VIEWSETS_PATH)
    def test_flows_failure_rolls_back_transfer(self, mock_change):
        mock_change.side_effect = FlowsChangeTicketerError(
            ticket_uuids=[str(self.room.ticket_uuid)],
            ticketer_uuid="ticketer-uuid",
            status_code=500,
        )

        response = self._patch_room({"queue_uuid": str(self.queue_b.uuid)})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.room.refresh_from_db()
        # Queue must NOT have changed because of rollback
        self.assertEqual(self.room.queue, self.queue_a)

    @patch(CHANGE_TICKETER_VIEWSETS_PATH)
    def test_flows_ticketer_not_found_rolls_back(self, mock_change):
        mock_change.side_effect = FlowsTicketerNotFoundError(
            sector_uuid=str(self.sector_b.uuid)
        )

        response = self._patch_room({"queue_uuid": str(self.queue_b.uuid)})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.room.refresh_from_db()
        self.assertEqual(self.room.queue, self.queue_a)


@override_settings(USE_WENI_FLOWS=True)
class BulkTransferChangeTicketerTests(_BaseTransferSetup):
    def _bulk_transfer(self, data):
        url = reverse("room-bulk_transfer")
        return self.client.post(url, data=data, format="json")

    @patch(CHANGE_TICKETER_BULK_PATH)
    def test_change_ticketer_called_when_sector_changes(self, mock_change):
        response = self._bulk_transfer(
            {
                "rooms_list": [str(self.room.uuid)],
                "queue_uuid": str(self.queue_b.uuid),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_change.assert_called_once()
        room_arg, sector_arg = mock_change.call_args.args
        self.assertEqual(room_arg.pk, self.room.pk)
        self.assertEqual(sector_arg, str(self.sector_b.uuid))

        self.room.refresh_from_db()
        self.assertEqual(self.room.queue, self.queue_b)

    @patch("chats.apps.rooms.models.Room.update_ticket")
    @patch(CHANGE_TICKETER_BULK_PATH)
    def test_change_ticketer_not_called_for_user_only_transfer(
        self, mock_change, _mock_update_ticket
    ):
        response = self._bulk_transfer(
            {
                "rooms_list": [str(self.room.uuid)],
                "user_email": "agent@test.com",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_change.assert_not_called()

    @patch(CHANGE_TICKETER_BULK_PATH)
    def test_flows_failure_rolls_back_room_change(self, mock_change):
        mock_change.side_effect = FlowsChangeTicketerError(
            ticket_uuids=[str(self.room.ticket_uuid)],
            ticketer_uuid="ticketer-uuid",
            status_code=500,
        )

        response = self._bulk_transfer(
            {
                "rooms_list": [str(self.room.uuid)],
                "queue_uuid": str(self.queue_b.uuid),
            }
        )

        # All-failed bulk transfers respond with 400 (see viewset)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        body = response.json()
        self.assertEqual(body["success_count"], 0)
        self.assertEqual(body["failed_count"], 1)
        self.assertIn(str(self.room.uuid), body["failed_rooms"])

        self.room.refresh_from_db()
        # Queue must NOT have changed because of rollback
        self.assertEqual(self.room.queue, self.queue_a)
