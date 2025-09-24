from unittest.mock import patch

from django.test import RequestFactory, TestCase
from rest_framework.test import force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.rooms.filters import RoomFilter
from chats.apps.api.v1.rooms.serializers import TransferRoomSerializer
from chats.apps.api.v1.rooms.viewsets import RoomViewset
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.models import Room


class RoomFilterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(email="agent@acme.com")
        self.project = Project.objects.create(name="P", timezone="UTC")
        self.sector = self.project.sectors.create(
            name="S", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.queue = self.sector.queues.create(name="Q")
        ProjectPermission.objects.create(project=self.project, user=self.user, role=1)

    @patch(
        "chats.apps.api.v1.rooms.filters.get_user_id_by_email_cached", return_value=None
    )
    def test_filter_project_returns_none_when_email_unknown(self, _):
        request = self.factory.get("/x?email=unknown@acme.com")
        request.user = self.user
        qs = Room.objects.all()
        f = RoomFilter(
            data={"project": str(self.project.pk)}, queryset=qs, request=request
        )
        self.assertFalse(f.qs.exists())


class TransferRoomSerializerTests(TestCase):
    @patch(
        "chats.apps.api.v1.rooms.serializers.get_user_id_by_email_cached",
        return_value=99,
    )
    def test_validate_sets_user_id_lower(self, _):
        s = TransferRoomSerializer(data={"user_email": "Agent@Acme.com"})
        s.is_valid(raise_exception=True)
        self.assertEqual(s.validated_data["user_id"], "agent@acme.com")


class RoomViewsetBulkTransferTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create(email="admin@acme.com")
        self.agent = User.objects.create(email="agent@acme.com")
        self.project = Project.objects.create(name="P", timezone="UTC")
        self.sector = self.project.sectors.create(
            name="S", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.queue = self.sector.queues.create(name="Q")
        self.perm = ProjectPermission.objects.create(
            project=self.project, user=self.agent, role=1
        )
        self.room = Room.objects.create(
            queue=self.queue, project_uuid=str(self.project.pk)
        )

    @patch("chats.apps.api.v1.rooms.viewsets.create_room_feedback_message")
    @patch("chats.apps.api.v1.rooms.viewsets.start_queue_priority_routing")
    @patch("chats.apps.api.v1.rooms.viewsets.get_user_id_by_email_cached")
    def test_bulk_transfer_assigns_user_instance(self, mock_cache, _routing, _feedback):
        mock_cache.return_value = self.agent.pk
        view = RoomViewset.as_view({"patch": "bulk_transfer"})
        req = self.factory.patch(
            "/x?user_email=agent@acme.com",
            data={"rooms_list": [str(self.room.uuid)]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        self.assertEqual(resp.status_code, 200)
        self.room.refresh_from_db()
        self.assertEqual(self.room.user, self.agent)

    @patch(
        "chats.apps.api.v1.rooms.viewsets.get_user_id_by_email_cached",
        return_value=None,
    )
    def test_bulk_transfer_returns_400_when_user_not_found(self, _):
        view = RoomViewset.as_view({"patch": "bulk_transfer"})
        req = self.factory.patch(
            "/x?user_email=no@acme.com",
            data={"rooms_list": [str(self.room.uuid)]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        self.assertEqual(resp.status_code, 400)
