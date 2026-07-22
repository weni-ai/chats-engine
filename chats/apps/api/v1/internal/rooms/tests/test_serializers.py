from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.rooms.serializers import RoomInternalListSerializer
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import MetricGoal, RoomMetrics
from chats.apps.projects.models import Project
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class RoomInternalListSerializerGoalsMetricsTests(TestCase):
    """Tests for ``goals_metrics`` on ``RoomInternalListSerializer``.

    Waiting-time goals for rooms still in the queue must compare against
    ``queue_time`` (now - added_to_queue_at), matching MetricGoalBreachService
    and the value the Insights awaiting screen displays.
    """

    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(name="Goals Metrics Project")
        cls.sector = Sector.objects.create(
            name="Test Sector",
            project=cls.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        cls.queue = Queue.objects.create(name="Test Queue", sector=cls.sector)
        cls.contact = Contact.objects.create(name="Client", email="client@test.com")
        cls.agent = User.objects.create_user(
            email="agent@test.com",
            password="secret",
            first_name="Jane",
            last_name="Doe",
        )
        cls.waiting_goal = MetricGoal.objects.create(
            project=cls.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=3600,
            unit=MetricGoal.UNIT_HOUR,
            is_active=True,
        )

    def _serialize(self, room: Room) -> dict:
        return RoomInternalListSerializer(
            room,
            context={
                "active_goals_by_metric": {
                    MetricGoal.METRIC_WAITING_TIME: self.waiting_goal,
                },
            },
        ).data

    def test_awaiting_room_exceeds_waiting_time_goal_via_queue_time(self):
        """Sala na fila com queue_time >= threshold → exceeded: true.

        RoomMetrics.waiting_time stays 0 while the room has no agent; the
        comparison must use queue_time (added_to_queue_at) instead.
        """
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=None,
            project_uuid=str(self.project.uuid),
            is_active=True,
        )
        Room.objects.filter(pk=room.pk).update(
            added_to_queue_at=timezone.now() - timedelta(seconds=14338),
        )
        room.refresh_from_db()
        RoomMetrics.objects.create(room=room, waiting_time=0)

        data = self._serialize(room)

        self.assertGreaterEqual(data["queue_time"], 3600)
        self.assertEqual(data["waiting_time"], 0)
        self.assertEqual(
            data["goals_metrics"],
            {"awaiting_time": {"exceeded": True}},
        )

    def test_awaiting_room_under_threshold_is_not_exceeded(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=None,
            project_uuid=str(self.project.uuid),
            is_active=True,
        )
        Room.objects.filter(pk=room.pk).update(
            added_to_queue_at=timezone.now() - timedelta(seconds=600),
        )
        room.refresh_from_db()

        data = self._serialize(room)

        self.assertLess(data["queue_time"], 3600)
        self.assertEqual(
            data["goals_metrics"],
            {"awaiting_time": {"exceeded": False}},
        )

    def test_assigned_room_waiting_time_goal_uses_queue_time_zero(self):
        """Once an agent is assigned, queue_time is 0 → exceeded: false."""
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
            project_uuid=str(self.project.uuid),
            is_active=True,
        )
        RoomMetrics.objects.create(room=room, waiting_time=7200)

        data = self._serialize(room)

        self.assertEqual(data["queue_time"], 0)
        self.assertEqual(
            data["goals_metrics"],
            {"awaiting_time": {"exceeded": False}},
        )

    def test_empty_goals_context_returns_empty_dict(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=None,
            project_uuid=str(self.project.uuid),
            is_active=True,
        )

        data = RoomInternalListSerializer(room, context={}).data

        self.assertEqual(data["goals_metrics"], {})
