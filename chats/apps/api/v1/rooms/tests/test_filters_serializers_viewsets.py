from unittest.mock import patch

from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.rooms.filters import RoomFilter
from chats.apps.api.v1.rooms.serializers import TransferRoomSerializer
from chats.apps.api.v1.rooms.viewsets import RoomViewset
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.models import Room, RoomPin


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
    @patch("chats.core.cache_utils.get_user_id_by_email_cached", return_value=99)
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

    def test_transfer_to_both_user_and_queue(self):
        view = RoomViewset.as_view({"patch": "bulk_transfer"})

        self.room.user = self.agent
        self.room.save()

        other_agent = User.objects.create(email="test@email.com")
        ProjectPermission.objects.create(project=self.project, user=other_agent, role=1)
        other_queue = self.sector.queues.create(name="Other Queue", sector=self.sector)

        req = self.factory.patch(
            f"/x?user_email={other_agent.email}&queue_uuid={other_queue.uuid}",
            data={"rooms_list": [str(self.room.uuid)]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.room.refresh_from_db()
        self.assertEqual(self.room.user, other_agent)
        self.assertEqual(self.room.queue, other_queue)


class RoomViewsetListTests(TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.request_user = User.objects.create(email="agent@acme.com")
        self.other_user = User.objects.create(email="other@acme.com")
        self.project = Project.objects.create(name="P", timezone="UTC")
        self.sector = self.project.sectors.create(
            name="S", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.queue = self.sector.queues.create(name="Q")
        ProjectPermission.objects.create(
            project=self.project, user=self.request_user, role=1
        )
        ProjectPermission.objects.create(
            project=self.project, user=self.other_user, role=1
        )
        self.view = RoomViewset.as_view({"get": "list"})
        self.contact_counter = 0
        self.feature_flag_patch = patch(
            "chats.apps.api.v1.rooms.viewsets.is_feature_active", return_value=True
        )
        self.feature_flag_patch.start()

    def tearDown(self):
        self.feature_flag_patch.stop()
        super().tearDown()

    def _new_contact(self):
        self.contact_counter += 1
        return Contact.objects.create(
            name=f"Contact {self.contact_counter}",
            email=f"contact{self.contact_counter}@test.com",
        )

    def _create_room(self, protocol: str, **overrides):
        defaults = {
            "queue": self.queue,
            "project_uuid": str(self.project.pk),
            "is_active": True,
            "contact": self._new_contact(),
            "protocol": protocol,
        }
        defaults.update(overrides)
        return Room.objects.create(**defaults)

    def _list(self, params=None, user=None):
        params = params or {}
        params.setdefault("project", str(self.project.pk))
        request = self.factory.get("/rooms", params)
        force_authenticate(request, user=user or self.request_user)
        return self.view(request)

    def test_pinned_rooms_prioritized_for_authenticated_user(self):
        pinned_room = self._create_room("PINNED", user=self.other_user)
        regular_room = self._create_room("REGULAR", user=self.other_user)

        RoomPin.objects.create(room=pinned_room, user=self.other_user)
        RoomPin.objects.create(room=regular_room, user=self.request_user)

        response = self._list({"email": self.other_user.email, "limit": 10})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertGreaterEqual(len(results), 2)

        self.assertEqual(results[0]["uuid"], str(pinned_room.uuid))
        self.assertEqual(results[1]["uuid"], str(regular_room.uuid))

    def test_list_handles_many_rooms_with_limited_queries(self):
        pinned_rooms = []
        for i in range(3005):
            room = self._create_room(protocol=f"ROOM-{i}")
            if i < 3:
                pinned_rooms.append(room)
        RoomPin.objects.bulk_create(
            [RoomPin(room=room, user=self.request_user) for room in pinned_rooms]
        )

        params = {"project": str(self.project.pk), "limit": 50}
        with CaptureQueriesContext(connection) as ctx:
            response = self._list(params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 3)
        # Ensure query count stays bounded even with thousands of rooms
        self.assertLessEqual(len(ctx), 400)

    def test_list_supports_common_filters(self):
        room_a = self._create_room("PROTO-123")
        self._create_room("PROTO-999")
        params_list = [
            {"project": str(self.project.pk), "room_status": "ongoing"},
            {"project": str(self.project.pk), "limit": 1, "offset": 1},
            {"project": str(self.project.pk), "search": "PROTO-123"},
        ]

        for params in params_list:
            with self.subTest(params=params):
                response = self._list(params)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn("results", response.data)

        search_response = self._list(
            {"project": str(self.project.pk), "search": "PROTO-123"}
        )
        self.assertTrue(
            any(item["uuid"] == str(room_a.uuid) for item in search_response.data["results"])
        )
