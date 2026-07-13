from datetime import time

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.logs.models import Log
from chats.apps.projects.models.models import Project
from chats.apps.sectors.models import Sector


class LogModelTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Test Sector",
            rooms_limit=5,
            work_start=time(hour=9, minute=0),
            work_end=time(hour=18, minute=0),
        )
        self.user = User.objects.create(email="logger@test.com")
        self.content_type = ContentType.objects.get_for_model(Sector)

    def test_creates_log_with_expected_fields(self):
        log = Log.objects.create(
            action=Log.Action.CREATE,
            content_type=self.content_type,
            object_id=self.sector.uuid,
            changes={"name": "Test Sector"},
            user=self.user,
            extra_info={"source": "test"},
            request_info={"ip": "127.0.0.1"},
        )

        self.assertEqual(log.action, Log.Action.CREATE)
        self.assertEqual(log.content_object, self.sector)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.extra_info, {"source": "test"})
        self.assertEqual(log.request_info, {"ip": "127.0.0.1"})

    def test_str_includes_action_and_object_id(self):
        log = Log.objects.create(
            action=Log.Action.UPDATE,
            content_type=self.content_type,
            object_id=self.sector.uuid,
            changes={},
        )

        self.assertIn(Log.Action.UPDATE, str(log))
        self.assertIn(str(self.sector.uuid), str(log))
