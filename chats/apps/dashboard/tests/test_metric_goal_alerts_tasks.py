"""Smoke tests for the metric goal alert Celery tasks."""

from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from chats.apps.api.utils import create_user_and_token
from chats.apps.contacts.models import Contact
from chats.apps.dashboard import tasks as dashboard_tasks
from chats.apps.dashboard.models import MetricGoal
from chats.apps.dashboard.services import metric_goal_alerts
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization


class _FakeRedis:
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


def _seed_room(project, queue):
    contact = Contact.objects.create(name="C", email="c@test.com")
    room = Room.objects.create(
        queue=queue,
        contact=contact,
        is_active=True,
        project_uuid=str(project.uuid),
    )
    past = timezone.now() - timedelta(seconds=300)
    Room.objects.filter(pk=room.pk).update(added_to_queue_at=past, user=None)


class CheckMetricGoalViolationsTaskTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Task Project")
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="08:00",
            work_end="18:00",
        )
        self.queue = self.sector.queues.create(name="queue")

        self.recipient, _ = create_user_and_token(nickname="recip")
        permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.recipient,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            permission=permission,
            sector=self.sector,
            role=SectorAuthorization.ROLE_MANAGER,
        )

        self.goal = MetricGoal.objects.create(
            project=self.project,
            metric=MetricGoal.METRIC_WAITING_TIME,
            threshold_seconds=60,
            rooms_threshold_count=1,
            email_enabled=True,
        )
        self.goal.recipients.add(permission)

        self.fake_redis = _FakeRedis()
        self.addCleanup(self._stop_patches)
        self._patches = [
            patch.object(
                metric_goal_alerts,
                "get_redis_connection",
                return_value=self.fake_redis,
            ),
            patch.object(dashboard_tasks, "send_channels_group"),
            # detect_violations and send_metric_goal_email each bind their own import.
            patch.object(
                metric_goal_alerts,
                "is_metric_goal_alerts_enabled",
                return_value=True,
            ),
            patch.object(
                dashboard_tasks,
                "is_metric_goal_alerts_enabled",
                return_value=True,
            ),
        ]
        started = [p.start() for p in self._patches]
        self.mock_send_group = started[1]

    def _stop_patches(self):
        for p in self._patches:
            p.stop()

    def test_violation_broadcasts_and_queues_email(self):
        _seed_room(self.project, self.queue)

        with patch.object(
            dashboard_tasks.send_metric_goal_email, "delay"
        ) as mock_delay:
            dashboard_tasks.check_metric_goal_violations()

        self.assertTrue(
            self.mock_send_group.called,
            "Expected at least one WebSocket broadcast",
        )
        first_call = self.mock_send_group.call_args_list[0]
        self.assertEqual(
            first_call.kwargs["group_name"],
            f"metric_goal_alerts:{self.project.uuid}",
        )
        self.assertEqual(first_call.kwargs["action"], "metric_goal.violated")
        self.assertEqual(first_call.kwargs["content"]["transition"], "new")

        self.assertTrue(mock_delay.called)
        kwargs = mock_delay.call_args.kwargs
        self.assertEqual(kwargs["project_uuid"], str(self.project.uuid))
        self.assertEqual(kwargs["metric"], MetricGoal.METRIC_WAITING_TIME)

    def test_send_metric_goal_email_dispatches_to_recipients(self):
        dashboard_tasks.send_metric_goal_email(
            project_uuid=str(self.project.uuid),
            metric=MetricGoal.METRIC_WAITING_TIME,
            violating_count=3,
            threshold_seconds=60,
            max_value_seconds=120,
            rooms_threshold_count=1,
        )
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn(self.recipient.email, sent.to)
        self.assertIn(self.project.name, sent.subject)

    def test_continuous_violation_emits_update_action(self):
        _seed_room(self.project, self.queue)
        with patch.object(dashboard_tasks.send_metric_goal_email, "delay"):
            dashboard_tasks.check_metric_goal_violations()

        self.mock_send_group.reset_mock()
        with patch.object(dashboard_tasks.send_metric_goal_email, "delay"):
            dashboard_tasks.check_metric_goal_violations()

        actions = [
            call.kwargs["action"] for call in self.mock_send_group.call_args_list
        ]
        self.assertIn("metric_goal.update", actions)
        self.assertNotIn("metric_goal.violated", actions)

    def test_send_metric_goal_email_skips_when_disabled(self):
        self.goal.email_enabled = False
        self.goal.save()
        dashboard_tasks.send_metric_goal_email(
            project_uuid=str(self.project.uuid),
            metric=MetricGoal.METRIC_WAITING_TIME,
            violating_count=3,
            threshold_seconds=60,
            max_value_seconds=120,
            rooms_threshold_count=1,
        )
        self.assertEqual(len(mail.outbox), 0)


class MetricGoalCeleryQueueRoutingTests(TestCase):
    """Risk alert tasks must publish to RISK_ALERT_CELERY_QUEUE."""

    def test_tasks_are_routed_to_risk_alert_queue(self):
        from django.conf import settings

        routes = getattr(settings, "CELERY_TASK_ROUTES", {})
        for task_name in (
            "check_metric_goal_violations",
            "send_metric_goal_email",
        ):
            self.assertIn(task_name, routes)
            self.assertEqual(
                routes[task_name]["queue"],
                settings.RISK_ALERT_CELERY_QUEUE,
            )

    def test_beat_schedule_publishes_to_risk_alert_queue(self):
        from django.conf import settings

        entry = settings.CELERY_BEAT_SCHEDULE["check-metric-goal-violations"]
        self.assertEqual(entry["options"]["queue"], settings.RISK_ALERT_CELERY_QUEUE)
