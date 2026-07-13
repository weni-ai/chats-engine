from datetime import time
from unittest.mock import MagicMock

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.logs.utils import (
    IGNORED_FIELDS,
    compute_changes,
    get_info_from_request,
    snapshot_instance,
)
from chats.apps.projects.models.models import Project
from chats.apps.sectors.models import Sector


class ComputeChangesTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Original Name",
            rooms_limit=5,
            work_start=time(hour=9, minute=0),
            work_end=time(hour=18, minute=0),
        )

    def test_create_returns_flat_snapshot(self):
        changes = compute_changes(None, self.sector)

        self.assertEqual(changes["name"], "Original Name")
        self.assertEqual(changes["rooms_limit"], 5)
        for field in IGNORED_FIELDS:
            self.assertNotIn(field, changes)

    def test_delete_returns_flat_snapshot(self):
        changes = compute_changes(self.sector, None)

        self.assertEqual(changes["name"], "Original Name")
        self.assertNotIn("uuid", changes)
        self.assertNotIn("created_on", changes)

    def test_update_includes_only_changed_fields(self):
        modified = Sector.objects.get(pk=self.sector.pk)
        modified.name = "New Name"
        modified.rooms_limit = 10

        changes = compute_changes(self.sector, modified)

        self.assertEqual(
            changes["name"], {"from": "Original Name", "to": "New Name"}
        )
        self.assertEqual(changes["rooms_limit"], {"from": 5, "to": 10})
        self.assertNotIn("project", changes)

    def test_update_excludes_system_and_audit_fields(self):
        modified = Sector.objects.get(pk=self.sector.pk)
        modified.name = "Changed"
        user = User.objects.create(email="audit@test.com")
        modified.modified_by = user

        changes = compute_changes(self.sector, modified)

        self.assertIn("name", changes)
        self.assertNotIn("modified_by", changes)
        self.assertNotIn("modified_by_id", changes)
        self.assertNotIn("uuid", changes)
        self.assertNotIn("created_on", changes)
        self.assertNotIn("modified_on", changes)

    def test_update_with_both_none_raises(self):
        with self.assertRaises(ValueError):
            compute_changes(None, None)

    def test_snapshot_serializes_foreign_keys_as_pk(self):
        snapshot = snapshot_instance(self.sector)

        self.assertEqual(snapshot["project"], str(self.project.pk))


class GetInfoFromRequestTests(TestCase):
    def test_extracts_ip_from_remote_addr(self):
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "10.0.0.1",
            "HTTP_USER_AGENT": "Mozilla/5.0",
        }

        info = get_info_from_request(request)

        self.assertEqual(info["ip"], "10.0.0.1")
        self.assertEqual(info["user_agent"], "Mozilla/5.0")

    def test_prefers_x_forwarded_for(self):
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "10.0.0.1",
            "HTTP_X_FORWARDED_FOR": "203.0.113.1, 10.0.0.1",
            "HTTP_USER_AGENT": "TestAgent/1.0",
        }

        info = get_info_from_request(request)

        self.assertEqual(info["ip"], "203.0.113.1")
        self.assertEqual(info["user_agent"], "TestAgent/1.0")
