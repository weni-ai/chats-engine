from datetime import time
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import ReportStatus
from chats.apps.projects.models.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class RoomExportEndpointTests(APITestCase):
    url_name = "chats-report-room"

    def setUp(self):
        self.user = User.objects.create_user(email="agent@example.com")
        self.project = Project.objects.create(name="Test Project")
        self.project_permission = ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(hour=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        QueueAuthorization.objects.create(
            permission=self.project_permission,
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
        )
        self.contact = Contact.objects.create(external_id="contact-1", name="Contact")
        self.room = Room.objects.create(
            contact=self.contact, queue=self.queue, user=self.user
        )
        Room.objects.filter(pk=self.room.pk).update(
            is_active=False, ended_at=self.room.created_on
        )
        self.room.refresh_from_db()

        self.client.force_authenticate(user=self.user)

    def _payload(self, **overrides):
        payload = {"room": str(self.room.uuid), "types": ["html", "pdf"]}
        payload.update(overrides)
        return payload

    @patch("chats.apps.api.v1.rooms.viewsets.generate_room_export")
    def test_creates_report_status_and_dispatches_task(self, mock_task):
        response = self.client.post(
            reverse(self.url_name), self._payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("report_uuid", response.json())

        report = ReportStatus.objects.get(uuid=response.json()["report_uuid"])
        self.assertEqual(report.report_type, ReportStatus.REPORT_TYPE_ROOM_EXPORT)
        self.assertEqual(report.status, "pending")
        self.assertEqual(report.room, self.room)
        self.assertEqual(report.user, self.user)
        self.assertEqual(report.project, self.project)
        self.assertEqual(sorted(report.fields_config["types"]), ["html", "pdf"])
        mock_task.delay.assert_called_once_with(str(report.uuid))

    @patch("chats.apps.api.v1.rooms.viewsets.generate_room_export")
    def test_rejects_active_room(self, mock_task):
        Room.objects.filter(pk=self.room.pk).update(is_active=True, ended_at=None)

        response = self.client.post(
            reverse(self.url_name), self._payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_task.delay.assert_not_called()

    @patch("chats.apps.api.v1.rooms.viewsets.generate_room_export")
    def test_rejects_user_without_permission(self, mock_task):
        outsider = User.objects.create_user(email="outsider@example.com")
        self.client.force_authenticate(user=outsider)

        response = self.client.post(
            reverse(self.url_name), self._payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_task.delay.assert_not_called()

    @patch("chats.apps.api.v1.rooms.viewsets.generate_room_export")
    def test_returns_404_when_room_does_not_exist(self, mock_task):
        response = self.client.post(
            reverse(self.url_name),
            self._payload(room="00000000-0000-0000-0000-000000000000"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_task.delay.assert_not_called()

    @patch("chats.apps.api.v1.rooms.viewsets.generate_room_export")
    def test_rejects_unsupported_format(self, mock_task):
        response = self.client.post(
            reverse(self.url_name),
            self._payload(types=["docx"]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_task.delay.assert_not_called()

    @patch("chats.apps.api.v1.rooms.viewsets.generate_room_export")
    def test_rejects_empty_types(self, mock_task):
        response = self.client.post(
            reverse(self.url_name),
            self._payload(types=[]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_task.delay.assert_not_called()

    @patch("chats.apps.api.v1.rooms.viewsets.generate_room_export")
    def test_returns_409_when_export_already_in_progress(self, mock_task):
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            room=self.room,
            report_type=ReportStatus.REPORT_TYPE_ROOM_EXPORT,
            fields_config={"types": ["html"]},
            status="in_progress",
        )

        response = self.client.post(
            reverse(self.url_name), self._payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        mock_task.delay.assert_not_called()

    @patch("chats.apps.api.v1.rooms.viewsets.generate_room_export")
    def test_allows_when_previous_export_is_ready(self, mock_task):
        ReportStatus.objects.create(
            project=self.project,
            user=self.user,
            room=self.room,
            report_type=ReportStatus.REPORT_TYPE_ROOM_EXPORT,
            fields_config={"types": ["html"]},
            status="ready",
        )

        response = self.client.post(
            reverse(self.url_name), self._payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_task.delay.assert_called_once()

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            reverse(self.url_name), self._payload(), format="json"
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    @patch("chats.apps.api.v1.rooms.viewsets.generate_room_export")
    def test_deduplicates_types(self, mock_task):
        response = self.client.post(
            reverse(self.url_name),
            self._payload(types=["html", "HTML", "pdf"]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        report = ReportStatus.objects.get(uuid=response.json()["report_uuid"])
        self.assertEqual(sorted(report.fields_config["types"]), ["html", "pdf"])
