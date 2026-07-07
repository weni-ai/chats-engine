"""Tests for the metric goal alert detection service."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import MetricGoal, RoomMetrics
from chats.apps.dashboard.services import metric_goal_alerts
from chats.apps.dashboard.services.metric_goal_alerts import (
    EMAIL_COOLDOWN_KEY_TEMPLATE,
    STATE_KEY_TEMPLATE,
    Violation,
    detect_violations,
    process_violations,
)
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


class FakeRedis:
    """Minimal redis-like store covering the operations used by the service."""

    def __init__(self):
        self.store: dict[str, bytes] = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return False
        self.store[key] = value.encode() if isinstance(value, str) else value
        return True

    def expire(self, key, _ttl):
        return key in self.store

    def delete(self, *keys):
        removed = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                removed += 1
        return removed

    def scan_iter(self, match=None):
        if match is None:
            yield from list(self.store.keys())
            return
        prefix, suffix = match.split("*", 1) if "*" in match else (match, "")
        for key in list(self.store.keys()):
            if key.startswith(prefix) and key.endswith(suffix):
                yield key


def _build_active_room(project, queue, *, user=None, age_seconds=0):
    """Create an active room dated ``age_seconds`` in the past."""
    contact = Contact.objects.create(name=f"contact-{timezone.now().timestamp()}")
    room = Room.objects.create(
        queue=queue,
        contact=contact,
        is_active=True,
        project_uuid=str(project.uuid),
    )
    past = timezone.now() - timedelta(seconds=age_seconds)
    if user is None:
        Room.objects.filter(pk=room.pk).update(
            added_to_queue_at=past, user=None
        )
    else:
        Room.objects.filter(pk=room.pk).update(
            added_to_queue_at=past,
            first_user_assigned_at=past,
            user_assigned_at=past,
            user=user,
        )
    room.refresh_from_db()
    return room


class DetectViolationsTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Detection project")
        self.sector = Sector.objects.create(
            name="sector",
            project=self.project,
            rooms_limit=10,
            work_start="08:00",
            work_end="18:00",
        )
        self.queue = self.sector.queues.create(name="queue")

    def test_returns_empty_when_no_active_goals(self):
        self.assertEqual(
            detect_violations(MetricGoal.METRIC_WAITING_TIME), []
        )

    def test_detects_waiting_time_when_threshold_reached(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=60,
            rooms_threshold_count=2,
        )
        for _ in range(3):
            _build_active_room(self.project, self.queue, age_seconds=300)

        results = detect_violations(MetricGoal.METRIC_WAITING_TIME)

        self.assertEqual(len(results), 1)
        violation = results[0]
        self.assertEqual(violation.project_uuid, str(self.project.uuid))
        self.assertEqual(violation.violating_count, 3)
        self.assertGreaterEqual(violation.max_value_seconds, 60)
        self.assertEqual(violation.rooms_threshold_count, 2)

    def test_violation_is_reported_even_when_below_email_threshold(self):
        """The WS/toast/widget alert fires with a single room in breach.

        `rooms_threshold_count` only gates the email notification (see
        `ProcessViolationsTestCase`) — it must not prevent the violation
        itself from being detected.
        """
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=60,
            rooms_threshold_count=5,
        )
        for _ in range(2):
            _build_active_room(self.project, self.queue, age_seconds=300)

        results = detect_violations(MetricGoal.METRIC_WAITING_TIME)

        self.assertEqual(len(results), 1)
        violation = results[0]
        self.assertEqual(violation.violating_count, 2)
        self.assertEqual(violation.rooms_threshold_count, 5)
        self.assertFalse(violation.meets_email_threshold)

    def test_skips_inactive_goals(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=60,
            rooms_threshold_count=1,
            is_active=False,
        )
        _build_active_room(self.project, self.queue, age_seconds=300)

        self.assertEqual(detect_violations(MetricGoal.METRIC_WAITING_TIME), [])

    def test_percent_threshold_uses_active_room_count(self):
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=60,
            rooms_threshold_count=999,
            rooms_threshold_percent=10,
        )
        for _ in range(10):
            _build_active_room(self.project, self.queue, age_seconds=300)

        results = detect_violations(MetricGoal.METRIC_WAITING_TIME)

        self.assertEqual(len(results), 1)
        violation = results[0]
        self.assertEqual(violation.rooms_threshold_count, 1)
        self.assertEqual(violation.active_rooms_count, 10)

    def test_detects_first_response_time(self):
        user = User.objects.create_user(email="frt-agent@example.com")
        self.project.permissions.create(user=user, role=1)
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_FIRST_RESPONSE_TIME,
            threshold_seconds=60,
            rooms_threshold_count=1,
        )
        responded_room = _build_active_room(
            self.project, self.queue, user=user, age_seconds=300
        )
        RoomMetrics.objects.create(room=responded_room, first_response_time=10)
        _build_active_room(self.project, self.queue, user=user, age_seconds=300)

        results = detect_violations(MetricGoal.METRIC_FIRST_RESPONSE_TIME)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].violating_count, 1)

    def test_detects_conversation_duration(self):
        user = User.objects.create_user(email="cd-agent@example.com")
        self.project.permissions.create(user=user, role=1)
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_CONVERSATION_DURATION,
            threshold_seconds=60,
            rooms_threshold_count=1,
        )
        _build_active_room(self.project, self.queue, user=user, age_seconds=300)

        results = detect_violations(MetricGoal.METRIC_CONVERSATION_DURATION)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].violating_count, 1)


class ProcessViolationsTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="State project")
        self.sector = Sector.objects.create(
            name="sector",
            project=self.project,
            rooms_limit=10,
            work_start="08:00",
            work_end="18:00",
        )
        self.queue = self.sector.queues.create(name="queue")
        MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=60,
            rooms_threshold_count=1,
            email_enabled=True,
        )
        self.fake_redis = FakeRedis()
        self.redis_patch = patch.object(
            metric_goal_alerts,
            "get_redis_connection",
            return_value=self.fake_redis,
        )
        self.redis_patch.start()
        self.addCleanup(self.redis_patch.stop)

    def _seed_violation(self):
        _build_active_room(self.project, self.queue, age_seconds=300)

    def test_first_run_emits_new_alert_and_email(self):
        self._seed_violation()
        new_alerts: list[Violation] = []
        emails: list[Violation] = []
        result = process_violations(
            MetricGoal.METRIC_WAITING_TIME,
            on_new_alert=new_alerts.append,
            on_email=emails.append,
        )
        self.assertEqual(len(new_alerts), 1)
        self.assertEqual(len(emails), 1)
        self.assertEqual(result.resolved, [])
        state_key = STATE_KEY_TEMPLATE.format(
            project_uuid=str(self.project.uuid),
            metric=MetricGoal.METRIC_WAITING_TIME,
        )
        cooldown_key = EMAIL_COOLDOWN_KEY_TEMPLATE.format(
            project_uuid=str(self.project.uuid),
            metric=MetricGoal.METRIC_WAITING_TIME,
        )
        self.assertIn(state_key, self.fake_redis.store)
        self.assertIn(cooldown_key, self.fake_redis.store)

    def test_second_run_emits_update_not_email(self):
        self._seed_violation()
        process_violations(
            MetricGoal.METRIC_WAITING_TIME,
            on_new_alert=lambda v: None,
            on_email=lambda v: None,
        )
        updates: list[Violation] = []
        emails: list[Violation] = []
        process_violations(
            MetricGoal.METRIC_WAITING_TIME,
            on_update=updates.append,
            on_email=emails.append,
        )
        self.assertEqual(len(updates), 1)
        self.assertEqual(len(emails), 0)

    def test_transition_to_ok_clears_state(self):
        self._seed_violation()
        process_violations(
            MetricGoal.METRIC_WAITING_TIME,
            on_new_alert=lambda v: None,
        )
        Room.objects.filter(project_uuid=str(self.project.uuid)).update(
            is_active=False
        )
        resolved: list[str] = []
        result = process_violations(
            MetricGoal.METRIC_WAITING_TIME,
            on_resolved=lambda uuid, metric: resolved.append(uuid),
        )
        self.assertEqual(resolved, [str(self.project.uuid)])
        state_key = STATE_KEY_TEMPLATE.format(
            project_uuid=str(self.project.uuid),
            metric=MetricGoal.METRIC_WAITING_TIME,
        )
        self.assertNotIn(state_key, self.fake_redis.store)
        self.assertEqual(result.resolved, [str(self.project.uuid)])

    def test_idempotent_under_repeated_sweeps(self):
        self._seed_violation()
        emails: list[Violation] = []
        for _ in range(3):
            process_violations(
                MetricGoal.METRIC_WAITING_TIME,
                on_new_alert=lambda v: None,
                on_update=lambda v: None,
                on_email=emails.append,
            )
        self.assertEqual(len(emails), 1)

    def test_email_skipped_when_email_disabled(self):
        MetricGoal.objects.filter(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
        ).update(email_enabled=False)
        self._seed_violation()
        emails: list[Violation] = []
        result = process_violations(
            MetricGoal.METRIC_WAITING_TIME,
            on_new_alert=lambda v: None,
            on_email=emails.append,
        )
        self.assertEqual(len(emails), 0)
        self.assertEqual(len(result.new_alerts), 1)

    def test_alert_fires_but_email_skipped_when_below_rooms_threshold(self):
        """A single breaching room is enough for the WS/toast alert, but the
        email must wait until `rooms_threshold_count` rooms are breaching.
        """
        MetricGoal.objects.filter(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
        ).update(rooms_threshold_count=5)
        self._seed_violation()

        new_alerts: list[Violation] = []
        emails: list[Violation] = []
        result = process_violations(
            MetricGoal.METRIC_WAITING_TIME,
            on_new_alert=new_alerts.append,
            on_email=emails.append,
        )

        self.assertEqual(len(new_alerts), 1)
        self.assertEqual(len(emails), 0)
        self.assertEqual(len(result.new_alerts), 1)
