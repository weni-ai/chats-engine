from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorTag


BASE_URL = "/v1/external/dashboard/{uuid}/finished_rooms_status/"


class BaseFinishedRoomsStatusTest(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.external_token = self.project.external_token

        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

        self.agent = User.objects.create(
            email="agent@test.com",
            first_name="Agent",
            last_name="Test",
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.now = timezone.now()

    def _url(self, project=None):
        uuid = project.uuid if project else self.project.uuid
        return BASE_URL.format(uuid=uuid)

    def _auth(self, token=None):
        t = token or self.external_token.uuid
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {t}")

    def _get(self, params=None, project=None):
        return self.client.get(self._url(project), params or {})

    def _make_room(self, *, is_active=False, ended_at=None, queue=None, user=None):
        """Creates a closed room in the current period by default."""
        return Room.objects.create(
            queue=queue or self.queue,
            user=user,
            is_active=is_active,
            ended_at=ended_at if ended_at is not None else self.now,
            first_user_assigned_at=self.now - timedelta(minutes=5),
        )

    def _make_metrics(self, room, *, waiting=0, first_response=0, interaction=0, message_response=0):
        return RoomMetrics.objects.create(
            room=room,
            waiting_time=waiting,
            first_response_time=first_response,
            interaction_time=interaction,
            message_response_time=message_response,
        )


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestFinishedRoomsStatusAuth(BaseFinishedRoomsStatusTest):
    def test_unauthenticated_request_returns_401(self):
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_bearer_token_returns_401(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer 00000000-0000-0000-0000-000000000000"
        )
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_from_other_project_cannot_access_this_project(self):
        other_project = Project.objects.create(name="Other", timezone="UTC")
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {other_project.external_token.uuid}"
        )
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_valid_token_returns_200(self):
        self._auth()
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


class TestFinishedRoomsStatusResponseShape(BaseFinishedRoomsStatusTest):
    def test_response_contains_all_expected_fields(self):
        self._auth()
        response = self._get()

        self.assertIn("finished", response.data)
        self.assertIn("average_waiting_time", response.data)
        self.assertIn("average_first_response_time", response.data)
        self.assertIn("average_response_time", response.data)
        self.assertIn("average_conversation_duration", response.data)

    def test_empty_project_returns_zeros(self):
        self._auth()
        response = self._get()

        self.assertEqual(response.data["finished"], 0)
        self.assertEqual(response.data["average_waiting_time"], 0.0)
        self.assertEqual(response.data["average_first_response_time"], 0.0)
        self.assertEqual(response.data["average_response_time"], 0.0)
        self.assertEqual(response.data["average_conversation_duration"], 0.0)


# ---------------------------------------------------------------------------
# finished count
# ---------------------------------------------------------------------------


class TestFinishedCount(BaseFinishedRoomsStatusTest):
    def test_counts_closed_rooms_in_period(self):
        self._make_room()
        self._make_room()

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        self.assertEqual(response.data["finished"], 2)

    def test_active_rooms_are_not_counted(self):
        self._make_room(is_active=True, ended_at=None)
        self._make_room()

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        self.assertEqual(response.data["finished"], 1)

    def test_rooms_outside_date_range_not_counted(self):
        yesterday = self.now - timedelta(days=2)
        self._make_room(ended_at=yesterday)
        self._make_room()

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        self.assertEqual(response.data["finished"], 1)

    def test_rooms_from_other_project_not_counted(self):
        other_project = Project.objects.create(name="Other", timezone="UTC")
        other_sector = Sector.objects.create(
            name="Other Sector",
            project=other_project,
            rooms_limit=5,
            work_start="00:00",
            work_end="23:59",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)
        Room.objects.create(queue=other_queue, is_active=False, ended_at=self.now)

        self._make_room()

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        self.assertEqual(response.data["finished"], 1)


# ---------------------------------------------------------------------------
# Date defaults
# ---------------------------------------------------------------------------


class TestDateDefaults(BaseFinishedRoomsStatusTest):
    def test_no_date_params_counts_rooms_from_today(self):
        self._make_room()

        old_room = self._make_room(ended_at=self.now - timedelta(days=2))
        # old_room should not be counted (before today's start)
        _ = old_room  # suppress unused variable warning

        self._auth()
        response = self._get()

        self.assertEqual(response.data["finished"], 1)

    def test_no_date_params_does_not_count_future_rooms(self):
        future = self.now + timedelta(hours=2)
        self._make_room(ended_at=future)

        self._auth()
        response = self._get()

        self.assertEqual(response.data["finished"], 0)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


class TestFilterBySector(BaseFinishedRoomsStatusTest):
    def setUp(self):
        super().setUp()
        self.sector2 = Sector.objects.create(
            name="Sector 2",
            project=self.project,
            rooms_limit=5,
            work_start="00:00",
            work_end="23:59",
        )
        self.queue2 = Queue.objects.create(name="Queue 2", sector=self.sector2)

    def test_filter_by_sector_returns_only_matching_rooms(self):
        self._make_room(queue=self.queue)
        self._make_room(queue=self.queue2)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({
            "start_date": today,
            "end_date": today,
            "sector": str(self.sector.uuid),
        })

        self.assertEqual(response.data["finished"], 1)

    def test_multiple_sector_filters(self):
        self._make_room(queue=self.queue)
        self._make_room(queue=self.queue2)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({
            "start_date": today,
            "end_date": today,
            "sector": [str(self.sector.uuid), str(self.sector2.uuid)],
        })

        self.assertEqual(response.data["finished"], 2)


class TestFilterByQueue(BaseFinishedRoomsStatusTest):
    def setUp(self):
        super().setUp()
        self.queue2 = Queue.objects.create(name="Queue 2", sector=self.sector)

    def test_filter_by_queue_returns_only_matching_rooms(self):
        self._make_room(queue=self.queue)
        self._make_room(queue=self.queue2)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({
            "start_date": today,
            "end_date": today,
            "queue": str(self.queue.uuid),
        })

        self.assertEqual(response.data["finished"], 1)

    def test_multiple_queue_filters(self):
        self._make_room(queue=self.queue)
        self._make_room(queue=self.queue2)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({
            "start_date": today,
            "end_date": today,
            "queue": [str(self.queue.uuid), str(self.queue2.uuid)],
        })

        self.assertEqual(response.data["finished"], 2)


class TestFilterByTag(BaseFinishedRoomsStatusTest):
    def setUp(self):
        super().setUp()
        self.tag1 = SectorTag.objects.create(name="Tag 1", sector=self.sector)
        self.tag2 = SectorTag.objects.create(name="Tag 2", sector=self.sector)

    def test_filter_by_tag_returns_only_tagged_rooms(self):
        tagged_room = self._make_room()
        tagged_room.tags.add(self.tag1)

        untagged_room = self._make_room()
        _ = untagged_room

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({
            "start_date": today,
            "end_date": today,
            "tag": str(self.tag1.uuid),
        })

        self.assertEqual(response.data["finished"], 1)

    def test_filter_by_multiple_tags_returns_rooms_with_any_tag(self):
        room1 = self._make_room()
        room1.tags.add(self.tag1)

        room2 = self._make_room()
        room2.tags.add(self.tag2)

        untagged = self._make_room()
        _ = untagged

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({
            "start_date": today,
            "end_date": today,
            "tag": [str(self.tag1.uuid), str(self.tag2.uuid)],
        })

        self.assertEqual(response.data["finished"], 2)


class TestFilterByAgent(BaseFinishedRoomsStatusTest):
    def setUp(self):
        super().setUp()
        self.agent2 = User.objects.create(
            email="agent2@test.com",
            first_name="Agent",
            last_name="Two",
        )
        ProjectPermission.objects.create(
            project=self.project,
            user=self.agent2,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

    def test_filter_by_agent_returns_only_that_agents_rooms(self):
        self._make_room(user=self.agent)
        self._make_room(user=self.agent2)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({
            "start_date": today,
            "end_date": today,
            "agent": self.agent.email,
        })

        self.assertEqual(response.data["finished"], 1)

    def test_agent_filter_also_applies_to_metrics(self):
        room_a1 = self._make_room(user=self.agent)
        self._make_metrics(room_a1, waiting=60)

        room_a2 = self._make_room(user=self.agent2)
        self._make_metrics(room_a2, waiting=120)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({
            "start_date": today,
            "end_date": today,
            "agent": self.agent.email,
        })

        self.assertEqual(response.data["finished"], 1)
        self.assertEqual(response.data["average_waiting_time"], 60.0)


# ---------------------------------------------------------------------------
# Metrics calculation
# ---------------------------------------------------------------------------


class TestMetricsCalculation(BaseFinishedRoomsStatusTest):
    def test_average_waiting_time(self):
        r1 = self._make_room()
        r2 = self._make_room()
        self._make_metrics(r1, waiting=60)
        self._make_metrics(r2, waiting=120)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        self.assertEqual(response.data["average_waiting_time"], 90.0)

    def test_average_first_response_time(self):
        r1 = self._make_room()
        r2 = self._make_room()
        self._make_metrics(r1, first_response=30)
        self._make_metrics(r2, first_response=90)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        self.assertEqual(response.data["average_first_response_time"], 60.0)

    def test_average_response_time_excludes_zero_values(self):
        r1 = self._make_room()
        r2 = self._make_room()
        # r2 has message_response_time=0, should be excluded from average
        self._make_metrics(r1, message_response=100)
        self._make_metrics(r2, message_response=0)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        self.assertEqual(response.data["average_response_time"], 100.0)

    def test_average_response_time_without_metrics_returns_zero(self):
        self._make_room()

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        self.assertEqual(response.data["average_response_time"], 0.0)

    def test_average_conversation_duration_uses_interaction_time(self):
        r1 = self._make_room()
        r2 = self._make_room()
        self._make_metrics(r1, interaction=300)
        self._make_metrics(r2, interaction=500)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        self.assertEqual(response.data["average_conversation_duration"], 400.0)

    def test_average_conversation_duration_excludes_rooms_without_agent_assignment(self):
        r1 = self._make_room()
        # r2 never had first_user_assigned_at set
        r2 = Room.objects.create(
            queue=self.queue,
            is_active=False,
            ended_at=self.now,
            first_user_assigned_at=None,
        )
        self._make_metrics(r1, interaction=200)
        self._make_metrics(r2, interaction=600)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        # Only r1 (with first_user_assigned_at) counts for conversation duration
        self.assertEqual(response.data["average_conversation_duration"], 200.0)
        # But both rooms count for finished
        self.assertEqual(response.data["finished"], 2)

    def test_rooms_without_metrics_contribute_zero_to_averages(self):
        r1 = self._make_room()
        self._make_room()  # no metrics
        self._make_metrics(r1, waiting=100)

        self._auth()
        today = self.now.strftime("%Y-%m-%d")
        response = self._get({"start_date": today, "end_date": today})

        # r2 has no metric record, so NULL is excluded from Avg by default in Django
        self.assertEqual(response.data["average_waiting_time"], 100.0)
        self.assertEqual(response.data["finished"], 2)
