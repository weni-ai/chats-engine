from datetime import time

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.logs.models import Log
from chats.apps.logs.usecases import CreateLogUseCase
from chats.apps.projects.models.models import Project
from chats.apps.sectors.models import Sector


class CreateLogUseCaseTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Test Sector",
            rooms_limit=5,
            work_start=time(hour=9, minute=0),
            work_end=time(hour=18, minute=0),
        )
        self.user = User.objects.create(email="manager@test.com")
        self.use_case = CreateLogUseCase()
        self.sector_ct = ContentType.objects.get_for_model(Sector)

    def test_create_action(self):
        log = self.use_case.execute(
            unchanged_object=None,
            object_with_changes=self.sector,
            user=self.user,
        )

        self.assertEqual(log.action, Log.Action.CREATE)
        self.assertEqual(log.content_type, self.sector_ct)
        self.assertEqual(log.object_id, self.sector.uuid)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.changes["name"], "Test Sector")
        self.assertNotIn("uuid", log.changes)

    def test_update_action(self):
        modified = Sector.objects.get(pk=self.sector.pk)
        modified.name = "Updated Sector"

        log = self.use_case.execute(
            unchanged_object=self.sector,
            object_with_changes=modified,
            user=self.user,
        )

        self.assertEqual(log.action, Log.Action.UPDATE)
        self.assertEqual(
            log.changes["name"],
            {"from": "Test Sector", "to": "Updated Sector"},
        )
        self.assertNotIn("rooms_limit", log.changes)

    def test_delete_action(self):
        log = self.use_case.execute(
            unchanged_object=self.sector,
            object_with_changes=None,
            user=self.user,
        )

        self.assertEqual(log.action, Log.Action.DELETE)
        self.assertEqual(log.object_id, self.sector.uuid)
        self.assertEqual(log.changes["name"], "Test Sector")

    def test_persists_extra_and_request_info(self):
        log = self.use_case.execute(
            unchanged_object=None,
            object_with_changes=self.sector,
            user=self.user,
            extra_info={"reason": "manual"},
            request_info={"ip": "192.168.0.1", "user_agent": "pytest"},
        )

        self.assertEqual(log.extra_info, {"reason": "manual"})
        self.assertEqual(
            log.request_info, {"ip": "192.168.0.1", "user_agent": "pytest"}
        )

    def test_defaults_empty_dicts_when_info_omitted(self):
        log = self.use_case.execute(
            unchanged_object=None,
            object_with_changes=self.sector,
        )

        self.assertEqual(log.extra_info, {})
        self.assertEqual(log.request_info, {})
        self.assertIsNone(log.user)

    def test_both_none_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(
                unchanged_object=None,
                object_with_changes=None,
            )

        self.assertIn("unchanged_object", str(ctx.exception))
