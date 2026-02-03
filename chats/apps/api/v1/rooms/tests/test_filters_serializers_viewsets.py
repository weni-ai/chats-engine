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
        self.feature_flag_eval_patch = patch(
            "chats.apps.feature_flags.services.FeatureFlagService.evaluate_feature_flag",
            return_value=True,
        )
        self.feature_flag_rules_patch = patch(
            "chats.apps.feature_flags.services.FeatureFlagService.get_feature_flag_rules",
            return_value=[],
        )
        self.feature_flag_patch.start()
        self.feature_flag_eval_patch.start()
        self.feature_flag_rules_patch.start()

    def tearDown(self):
        self.feature_flag_patch.stop()
        self.feature_flag_eval_patch.stop()
        self.feature_flag_rules_patch.stop()
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
        # With the optimized pin version, query count should be much lower
        # The key is filtering FIRST, then annotating only necessary rooms
        # This prevents the O(N) annotation problem that caused production issues
        self.assertLessEqual(
            len(ctx), 50,
            f"Query count too high: {len(ctx)}. The optimized version should stay under 50 queries."
        )

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

    def test_optimized_pin_order_filters_before_annotating(self):
        """
        Test that the optimized version filters BEFORE annotating,
        which is critical for performance with large datasets.
        """
        # Create rooms with different statuses
        active_pinned = self._create_room("ACTIVE-PINNED", is_active=True)
        active_regular = self._create_room("ACTIVE-REGULAR", is_active=True)
        inactive_pinned = self._create_room("INACTIVE-PINNED", is_active=False)

        # Pin both pinned rooms
        RoomPin.objects.create(room=active_pinned, user=self.request_user)
        RoomPin.objects.create(room=inactive_pinned, user=self.request_user)

        # Request only active rooms
        params = {
            "project": str(self.project.pk),
            "is_active": "true",
            "limit": 50
        }

        with CaptureQueriesContext(connection) as ctx:
            response = self._list(params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]

        # Should include active pinned room first, then active regular
        result_uuids = [r["uuid"] for r in results]
        self.assertIn(str(active_pinned.uuid), result_uuids)
        self.assertIn(str(active_regular.uuid), result_uuids)

        # Should NOT include inactive pinned room (filters applied correctly)
        self.assertNotIn(str(inactive_pinned.uuid), result_uuids)

        # Pinned room should come first
        if len(results) >= 2:
            self.assertEqual(results[0]["uuid"], str(active_pinned.uuid))

        # Query count should be reasonable even with filters
        self.assertLessEqual(
            len(ctx), 50,
            f"Too many queries with filters: {len(ctx)}"
        )

class RoomViewsetBulkCloseTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create(email="admin@acme.com")
        self.agent = User.objects.create(email="agent@acme.com")
        self.project = Project.objects.create(name="P", timezone="UTC")
        self.sector = self.project.sectors.create(
            name="S", 
            rooms_limit=5, 
            work_start="08:00", 
            work_end="18:00",
            is_csat_enabled=False
        )
        self.queue = self.sector.queues.create(name="Q")
        self.perm_admin = ProjectPermission.objects.create(
            project=self.project, user=self.admin, role=ProjectPermission.ROLE_ADMIN
        )
        self.perm_agent = ProjectPermission.objects.create(
            project=self.project, user=self.agent, role=ProjectPermission.ROLE_AGENT
        )

    def test_bulk_close_single_room(self):
        """Test closing a single room via API"""
        room = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=True
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": [{"uuid": str(room.uuid)}]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["success_count"], 1)
        self.assertEqual(resp.data["failed_count"], 0)
        self.assertTrue(resp.data["success"])
        
        room.refresh_from_db()
        self.assertFalse(room.is_active)
        self.assertIsNotNone(room.ended_at)

    def test_bulk_close_multiple_rooms(self):
        """Test closing multiple rooms via API"""
        rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=str(self.project.pk),
                is_active=True
            )
            for _ in range(5)
        ]
        rooms_data = [{"uuid": str(room.uuid)} for room in rooms]
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": rooms_data},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["success_count"], 5)
        self.assertEqual(resp.data["failed_count"], 0)
        
        # Verify all rooms are closed
        for room in rooms:
            room.refresh_from_db()
            self.assertFalse(room.is_active)

    def test_bulk_close_with_tags(self):
        """Test closing rooms with specific tags per room"""
        from chats.apps.sectors.models import SectorTag
        
        room = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=True
        )
        tag = SectorTag.objects.create(name="TestTag", sector=self.sector)
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={
                "rooms": [
                    {
                        "uuid": str(room.uuid),
                        "tags": [str(tag.uuid)]
                    }
                ]
            },
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        room.refresh_from_db()
        self.assertIn(tag, room.tags.all())

    def test_bulk_close_with_end_by(self):
        """Test closing rooms with end_by parameter"""
        room = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=True
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={
                "rooms": [{"uuid": str(room.uuid)}],
                "end_by": "system"
            },
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        room.refresh_from_db()
        self.assertEqual(room.ended_by, "system")

    def test_bulk_close_with_closed_by(self):
        """Test closing rooms with closed_by parameter"""
        room = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=True
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={
                "rooms": [{"uuid": str(room.uuid)}],
                "closed_by_email": self.agent.email
            },
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        room.refresh_from_db()
        self.assertEqual(room.closed_by, self.agent)

    def test_bulk_close_returns_404_for_no_active_rooms(self):
        """Test that 404 is returned when no active rooms found"""
        room = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=False  # Already closed
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": [{"uuid": str(room.uuid)}]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_close_validates_permissions(self):
        """Test that user must have permissions on project"""
        other_project = Project.objects.create(name="Other Project", timezone="UTC")
        other_sector = other_project.sectors.create(
            name="Other Sector",
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00"
        )
        other_queue = other_sector.queues.create(name="Other Queue")
        other_room = Room.objects.create(
            queue=other_queue,
            project_uuid=str(other_project.pk),
            is_active=True
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": [{"uuid": str(other_room.uuid)}]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)  # Admin doesn't have permission on other_project
        resp = view(req)
        
        # Should fail validation
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_close_ignores_already_closed_rooms(self):
        """Test that already closed rooms are tracked as failures"""
        room1 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=True
        )
        room2 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=False  # Already closed
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": [
                {"uuid": str(room1.uuid)},
                {"uuid": str(room2.uuid)}
            ]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_207_MULTI_STATUS)  # Partial success
        self.assertEqual(resp.data["success_count"], 1)
        self.assertEqual(resp.data["failed_count"], 1)
        self.assertIn(str(room2.uuid), resp.data["failed_rooms"])

    def test_bulk_close_rooms_in_queue(self):
        """Test closing rooms that are in queue (not assigned)"""
        room1 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            user=None,  # In queue
            is_active=True
        )
        room2 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            user=None,  # In queue
            is_active=True
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": [
                {"uuid": str(room1.uuid)},
                {"uuid": str(room2.uuid)}
            ]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["success_count"], 2)
        self.assertEqual(resp.data["failed_count"], 0)

    def test_bulk_close_rooms_in_progress(self):
        """Test closing rooms that are in progress (assigned)"""
        room1 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            user=self.agent,  # Assigned
            is_active=True
        )
        room2 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            user=self.agent,  # Assigned
            is_active=True
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": [
                {"uuid": str(room1.uuid)},
                {"uuid": str(room2.uuid)}
            ]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["success_count"], 2)
        self.assertEqual(resp.data["failed_count"], 0)

    def test_bulk_close_validates_max_rooms_limit(self):
        """Test that serializer validates max rooms limit"""
        # Create more than 5000 room UUIDs
        import uuid
        rooms_data = [{"uuid": str(uuid.uuid4())} for _ in range(5001)]
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": rooms_data},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        # Should fail validation
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_bulk_close_all_failed(self):
        """Test response when all rooms fail to close"""
        room1 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=False  # Already closed
        )
        room2 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=False  # Already closed
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": [
                {"uuid": str(room1.uuid)},
                {"uuid": str(room2.uuid)}
            ]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["success_count"], 0)
        self.assertEqual(resp.data["failed_count"], 2)
        self.assertFalse(resp.data["success"])
        self.assertEqual(len(resp.data["errors"]), 2)
    
    def test_bulk_close_partial_success(self):
        """Test response when some rooms succeed and some fail"""
        room1 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=True  # Will succeed
        )
        room2 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=False  # Will fail (already closed)
        )
        room3 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=True  # Will succeed
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": [
                {"uuid": str(room1.uuid)},
                {"uuid": str(room2.uuid)},
                {"uuid": str(room3.uuid)}
            ]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(resp.data["success_count"], 2)
        self.assertEqual(resp.data["failed_count"], 1)
        self.assertTrue(resp.data["success"])
        self.assertEqual(resp.data["total_processed"], 3)
        self.assertIn("errors", resp.data)
        self.assertIn("failed_rooms", resp.data)
    
    def test_bulk_close_returns_error_details(self):
        """Test that error details are returned in response"""
        room = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=False  # Already closed
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": [{"uuid": str(room.uuid)}]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertIn("errors", resp.data)
        self.assertGreater(len(resp.data["errors"]), 0)
        self.assertIn("already closed", resp.data["errors"][0].lower())
        self.assertIn(str(room.uuid), resp.data["failed_rooms"])
    
    def test_bulk_close_with_different_tags_per_room(self):
        """Test closing multiple rooms with different tags for each"""
        from chats.apps.sectors.models import SectorTag
        
        room1 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=True
        )
        room2 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=True
        )
        room3 = Room.objects.create(
            queue=self.queue,
            project_uuid=str(self.project.pk),
            is_active=True
        )
        
        tag1 = SectorTag.objects.create(name="Tag1", sector=self.sector)
        tag2 = SectorTag.objects.create(name="Tag2", sector=self.sector)
        tag3 = SectorTag.objects.create(name="Tag3", sector=self.sector)
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={
                "rooms": [
                    {"uuid": str(room1.uuid), "tags": [str(tag1.uuid)]},
                    {"uuid": str(room2.uuid), "tags": [str(tag2.uuid), str(tag3.uuid)]},
                    {"uuid": str(room3.uuid)}  # No tags
                ]
            },
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["success_count"], 3)
        
        room1.refresh_from_db()
        room2.refresh_from_db()
        room3.refresh_from_db()
        
        # Verify each room has correct tags
        self.assertEqual(room1.tags.count(), 1)
        self.assertIn(tag1, room1.tags.all())
        
        self.assertEqual(room2.tags.count(), 2)
        self.assertIn(tag2, room2.tags.all())
        self.assertIn(tag3, room2.tags.all())
        
        self.assertEqual(room3.tags.count(), 0)
    
    def test_bulk_close_with_required_tags_fails_if_no_tags(self):
        """Test that rooms requiring tags fail validation if no tags provided"""
        from chats.apps.sectors.models import SectorTag
        from chats.apps.queues.models import Queue
        
        # Create a queue that requires tags
        queue_with_required_tags = Queue.objects.create(
            name="Required Tags Queue",
            sector=self.sector,
            required_tags=True
        )
        
        room = Room.objects.create(
            queue=queue_with_required_tags,
            project_uuid=str(self.project.pk),
            is_active=True
        )
        
        view = RoomViewset.as_view({"post": "bulk_close"})
        req = self.factory.post(
            "/x",
            data={"rooms": [{"uuid": str(room.uuid)}]},
            content_type="application/json",
        )
        force_authenticate(req, user=self.admin)
        resp = view(req)
        
        # Should fail because tags are required
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["success_count"], 0)
        self.assertEqual(resp.data["failed_count"], 1)
        self.assertIn("required", resp.data["errors"][0].lower())
