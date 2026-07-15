from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.dto import Filters
from chats.apps.api.v1.dashboard.metric_goals.constants import (
    threshold_seconds_to_unit_value,
)
from chats.apps.api.v1.dashboard.metric_goals.services import (
    MetricGoalBreachService,
)
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import MetricGoal, RoomMetrics
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class ThresholdSecondsToUnitValueTests(TestCase):
    def test_seconds_unit_returns_same_value(self):
        self.assertEqual(threshold_seconds_to_unit_value(300, "s"), 300)

    def test_minutes_unit_divides_correctly(self):
        self.assertEqual(threshold_seconds_to_unit_value(300, "m"), 5)

    def test_hours_unit_divides_correctly(self):
        self.assertEqual(threshold_seconds_to_unit_value(7200, "h"), 2)

    def test_unknown_unit_falls_back_to_raw_value(self):
        self.assertEqual(threshold_seconds_to_unit_value(300, "x"), 300)


class MetricGoalBreachServiceTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.user = User.objects.create_user(email="agent@test.com")
        self.service = MetricGoalBreachService()

    def _new_contact(self, suffix: str) -> Contact:
        return Contact.objects.create(
            name=f"Contact {suffix}", external_id=f"ext-{suffix}"
        )

    def _waiting_room(self, *, since_seconds: int, suffix: str) -> Room:
        room = Room.objects.create(
            queue=self.queue,
            contact=self._new_contact(suffix),
            user=None,
            is_active=True,
        )
        Room.objects.filter(uuid=room.uuid).update(
            added_to_queue_at=timezone.now() - timedelta(seconds=since_seconds)
        )
        room.refresh_from_db()
        return room

    def _assigned_room(
        self,
        *,
        since_seconds: int,
        suffix: str,
        first_response_time: int = None,
    ) -> Room:
        room = Room.objects.create(
            queue=self.queue,
            contact=self._new_contact(suffix),
            user=self.user,
            is_active=True,
        )
        Room.objects.filter(uuid=room.uuid).update(
            first_user_assigned_at=timezone.now()
            - timedelta(seconds=since_seconds)
        )
        if first_response_time is not None:
            RoomMetrics.objects.create(
                room=room,
                first_response_time=first_response_time,
            )
        room.refresh_from_db()
        return room

    def test_returns_empty_dict_when_no_goals_configured(self):
        payload = self.service.get_goals_payload(self.project)

        self.assertEqual(payload, {})

    def test_omits_inactive_goals(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
            is_active=False,
        )

        payload = self.service.get_goals_payload(self.project)

        self.assertEqual(payload, {})

    def test_returns_goal_entry_for_each_active_metric(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=120,
            unit=MetricGoal.UNIT_MINUTE,
        )
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_FIRST_RESPONSE_TIME,
            threshold_seconds=60,
            unit=MetricGoal.UNIT_MINUTE,
        )

        payload = self.service.get_goals_payload(self.project)

        self.assertIn("waiting_time_goal", payload)
        self.assertIn("first_response_time_goal", payload)
        self.assertNotIn("conversation_duration_goal", payload)

    def test_threshold_value_reflects_configured_unit(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_MINUTE,
        )

        payload = self.service.get_goals_payload(self.project)

        entry = payload["waiting_time_goal"]
        self.assertEqual(entry["threshold_seconds"], 300)
        self.assertEqual(entry["threshold_value"], 5)
        self.assertEqual(entry["unit"], MetricGoal.UNIT_MINUTE)

    def test_waiting_time_breach_counts_only_rooms_above_threshold(self):
        self._waiting_room(since_seconds=10, suffix="under-1")
        self._waiting_room(since_seconds=400, suffix="over-1")
        self._waiting_room(since_seconds=500, suffix="over-2")

        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
            rooms_threshold_count=5,
        )

        payload = self.service.get_goals_payload(self.project)

        entry = payload["waiting_time_goal"]
        self.assertEqual(entry["breached_rooms_count"], 2)
        # The widget alert is not gated by rooms_threshold_count (that only
        # gates the email notification) — 2 rooms breaching is enough.
        self.assertTrue(entry["is_breached"])

    def test_waiting_time_is_breached_with_a_single_room_over_threshold(self):
        self._waiting_room(since_seconds=400, suffix="over-1")

        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
            rooms_threshold_count=5,
        )

        entry = self.service.get_goals_payload(self.project)["waiting_time_goal"]

        self.assertEqual(entry["breached_rooms_count"], 1)
        self.assertTrue(entry["is_breached"])

    def test_first_response_time_skips_rooms_already_responded(self):
        # Already responded — must NOT count as breach.
        self._assigned_room(since_seconds=400, suffix="responded", first_response_time=120)
        # Still waiting for first response — counts as breach.
        self._assigned_room(since_seconds=400, suffix="pending")

        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_FIRST_RESPONSE_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
            rooms_threshold_count=1,
        )

        entry = self.service.get_goals_payload(
            self.project
        )["first_response_time_goal"]

        self.assertEqual(entry["breached_rooms_count"], 1)
        self.assertTrue(entry["is_breached"])

    def test_conversation_duration_breach_counts_long_conversations(self):
        self._assigned_room(since_seconds=100, suffix="short")
        self._assigned_room(since_seconds=900, suffix="long-1")
        self._assigned_room(since_seconds=1500, suffix="long-2")

        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_CONVERSATION_DURATION,
            threshold_seconds=600,
            unit=MetricGoal.UNIT_SECOND,
            rooms_threshold_count=2,
        )

        entry = self.service.get_goals_payload(
            self.project
        )["conversation_duration_goal"]

        self.assertEqual(entry["breached_rooms_count"], 2)
        self.assertTrue(entry["is_breached"])

    def test_filters_narrow_breach_count_by_sector(self):
        other_sector = Sector.objects.create(
            name="Other",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other Queue", sector=other_sector)

        # Breach inside the main sector.
        self._waiting_room(since_seconds=400, suffix="main")
        # Breach inside another sector — must be filtered out.
        room_other = Room.objects.create(
            queue=other_queue,
            contact=self._new_contact("other"),
            user=None,
            is_active=True,
        )
        Room.objects.filter(uuid=room_other.uuid).update(
            added_to_queue_at=timezone.now() - timedelta(seconds=400)
        )

        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
            rooms_threshold_count=1,
        )

        filters = Filters(
            project=self.project,
            sector=[str(self.sector.uuid)],
        )

        entry = self.service.get_goals_payload(
            self.project, filters
        )["waiting_time_goal"]

        # Only the room from the filtered sector counts.
        self.assertEqual(entry["breached_rooms_count"], 1)

    def test_zero_breaches_returns_is_breached_false(self):
        self._waiting_room(since_seconds=10, suffix="under")

        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=300,
            unit=MetricGoal.UNIT_SECOND,
            rooms_threshold_count=1,
        )

        entry = self.service.get_goals_payload(self.project)["waiting_time_goal"]

        self.assertEqual(entry["breached_rooms_count"], 0)
        self.assertFalse(entry["is_breached"])
