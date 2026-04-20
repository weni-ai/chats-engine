import datetime
from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.quickmessages.models import QuickMessage
from chats.apps.sectors.models import (
    GroupSector,
    Sector,
    SectorAuthorization,
    SectorHoliday,
    SectorTag,
)

# ---------------------------------------------------------------------------
# AuditableMixin — created_by / modified_by
# ---------------------------------------------------------------------------


class AuditableMixinCreateUpdateTests(TestCase):
    def setUp(self):
        patcher = patch(
            "chats.core.models.is_feature_active_for_attributes", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.user = User.objects.create_user(email="audit@test.com", password="x")
        self.other_user = User.objects.create_user(email="other@test.com", password="x")
        self.project = Project.objects.create(name="Audit Project", timezone="UTC")

    def _make_sector(self, name="Sector Audit", created_by=None, modified_by=None):
        return Sector.objects.create(
            name=name,
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
            created_by=created_by,
            modified_by=modified_by,
        )

    def test_created_by_is_set_on_creation(self):
        sector = self._make_sector(created_by=self.user, modified_by=self.user)
        self.assertEqual(sector.created_by, self.user)

    def test_modified_by_is_set_on_creation(self):
        sector = self._make_sector(created_by=self.user, modified_by=self.user)
        self.assertEqual(sector.modified_by, self.user)

    def test_modified_by_is_updated_on_save(self):
        sector = self._make_sector(created_by=self.user, modified_by=self.user)

        sector.rooms_limit = 10
        sector.modified_by = self.other_user
        sector.save()

        sector.refresh_from_db()
        self.assertEqual(sector.modified_by, self.other_user)

    def test_created_by_is_not_overwritten_on_update(self):
        sector = self._make_sector(created_by=self.user, modified_by=self.user)

        sector.rooms_limit = 10
        sector.modified_by = self.other_user
        sector.save()

        sector.refresh_from_db()
        self.assertEqual(sector.created_by, self.user)

    def test_fields_are_null_when_not_provided(self):
        sector = self._make_sector("No User Sector")
        self.assertIsNone(sector.created_by)
        self.assertIsNone(sector.modified_by)


# ---------------------------------------------------------------------------
# AuditableMixin — deleted_by (soft delete)
# ---------------------------------------------------------------------------


class AuditableMixinSoftDeleteTests(TestCase):
    def setUp(self):
        patcher = patch(
            "chats.core.models.is_feature_active_for_attributes", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.user = User.objects.create_user(email="deleter@test.com", password="x")
        self.project = Project.objects.create(name="Delete Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Sector To Delete",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )

    def test_deleted_by_is_set_on_soft_delete(self):
        self.sector.deleted_by = self.user
        self.sector.modified_by = self.user
        self.sector.is_deleted = True
        self.sector.save()

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.deleted_by, self.user)

    def test_deleted_by_is_not_set_when_is_deleted_is_false(self):
        self.sector.modified_by = self.user
        self.sector.rooms_limit = 10
        self.sector.save()

        self.sector.refresh_from_db()
        self.assertIsNone(self.sector.deleted_by)

    def test_deleted_by_is_null_when_not_provided(self):
        self.sector.is_deleted = True
        self.sector.save()

        self.sector.refresh_from_db()
        self.assertIsNone(self.sector.deleted_by)

    def test_deleted_by_is_not_overwritten_if_already_set(self):
        first_user = User.objects.create_user(email="first@test.com", password="x")
        second_user = User.objects.create_user(email="second@test.com", password="x")

        self.sector.deleted_by = first_user
        self.sector.is_deleted = True
        self.sector.save()

        self.sector.modified_by = second_user
        self.sector.save()

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.deleted_by, first_user)

    def test_deleted_by_is_set_via_sector_holiday_soft_delete(self):
        """Covers the SectorHoliday.delete() override path with explicit user."""
        holiday = SectorHoliday.objects.create(
            sector=self.sector,
            date=datetime.date(2025, 12, 25),
            day_type=SectorHoliday.CLOSED,
        )
        holiday.deleted_by = self.user
        holiday.modified_by = self.user
        holiday.delete()

        holiday.refresh_from_db()
        self.assertEqual(holiday.deleted_by, self.user)


# ---------------------------------------------------------------------------
# AuditableMixin — feature flag gating (OFF / unreachable)
# ---------------------------------------------------------------------------


class AuditableMixinFlagOffTests(TestCase):
    """
    With the audit feature flag OFF, the mixin must:
    - Drop caller-provided audit values on create (fields stay NULL).
    - Restore original DB values on update (historical data is preserved).
    """

    def setUp(self):
        self.user = User.objects.create_user(email="ff@test.com", password="x")
        self.other_user = User.objects.create_user(email="ff2@test.com", password="x")
        self.project = Project.objects.create(name="Flag Project", timezone="UTC")

    def _make_sector_with_flag(self, flag_value, **kwargs):
        with patch(
            "chats.core.models.is_feature_active_for_attributes",
            return_value=flag_value,
        ):
            return Sector.objects.create(
                name=kwargs.pop("name", "Flag Sector"),
                project=self.project,
                rooms_limit=5,
                work_start="08:00",
                work_end="18:00",
                **kwargs,
            )

    def test_created_by_is_dropped_on_create_when_flag_off(self):
        sector = self._make_sector_with_flag(
            False, created_by=self.user, modified_by=self.user
        )
        sector.refresh_from_db()
        self.assertIsNone(sector.created_by)
        self.assertIsNone(sector.modified_by)

    def test_created_by_is_preserved_on_update_when_flag_toggles_off(self):
        """Regression: flag toggling off after creation must NOT erase history."""
        sector = self._make_sector_with_flag(
            True, created_by=self.user, modified_by=self.user
        )

        with patch(
            "chats.core.models.is_feature_active_for_attributes", return_value=False
        ):
            sector.rooms_limit = 10
            sector.modified_by = self.other_user
            sector.save()

        sector.refresh_from_db()
        self.assertEqual(sector.created_by, self.user)

    def test_modified_by_is_not_updated_when_flag_off(self):
        sector = self._make_sector_with_flag(
            True, created_by=self.user, modified_by=self.user
        )

        with patch(
            "chats.core.models.is_feature_active_for_attributes", return_value=False
        ):
            sector.rooms_limit = 20
            sector.modified_by = self.other_user
            sector.save()

        sector.refresh_from_db()
        self.assertEqual(sector.modified_by, self.user)

    def test_deleted_by_is_not_written_on_soft_delete_when_flag_off(self):
        sector = self._make_sector_with_flag(
            True, created_by=self.user, modified_by=self.user
        )

        with patch(
            "chats.core.models.is_feature_active_for_attributes", return_value=False
        ):
            sector.deleted_by = self.other_user
            sector.is_deleted = True
            sector.save()

        sector.refresh_from_db()
        self.assertIsNone(sector.deleted_by)
        self.assertTrue(sector.is_deleted)

    def test_caller_values_are_kept_when_flag_service_raises(self):
        """Fail-open behavior: unreachable flag service must not erase data."""
        with patch(
            "chats.core.models.is_feature_active_for_attributes",
            side_effect=RuntimeError("flag service down"),
        ):
            sector = Sector.objects.create(
                name="Fail Open Sector",
                project=self.project,
                rooms_limit=5,
                work_start="08:00",
                work_end="18:00",
                created_by=self.user,
                modified_by=self.user,
            )

        sector.refresh_from_db()
        self.assertEqual(sector.created_by, self.user)
        self.assertEqual(sector.modified_by, self.user)

    def test_audit_is_dropped_when_project_is_unavailable(self):
        """
        Fail-closed when no project context is available to evaluate the flag
        (e.g. QuickMessage without sector). The flag service must not even be
        consulted, and audit fields must stay NULL on create.
        """
        with patch(
            "chats.core.models.is_feature_active_for_attributes"
        ) as mock_flag:
            qm = QuickMessage.objects.create(
                user=self.user,
                shortcut="/oi",
                text="Olá",
                created_by=self.user,
                modified_by=self.user,
            )

        mock_flag.assert_not_called()
        qm.refresh_from_db()
        self.assertIsNone(qm.created_by)
        self.assertIsNone(qm.modified_by)

    def test_audit_is_written_for_quick_message_with_sector_when_flag_on(self):
        """Positive control for the QuickMessage path: with sector + flag ON, audit persists."""
        sector = self._make_sector_with_flag(True)

        with patch(
            "chats.core.models.is_feature_active_for_attributes", return_value=True
        ):
            qm = QuickMessage.objects.create(
                user=self.user,
                shortcut="/oi",
                text="Olá",
                sector=sector,
                created_by=self.user,
                modified_by=self.user,
            )

        qm.refresh_from_db()
        self.assertEqual(qm.created_by, self.user)
        self.assertEqual(qm.modified_by, self.user)


# ---------------------------------------------------------------------------
# AuditableMixin._get_project — all models
# ---------------------------------------------------------------------------


class AuditableMixinGetProjectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="proj@test.com", password="x")
        self.project = Project.objects.create(name="GP Project", timezone="UTC")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="GP Sector",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="GP Queue", sector=self.sector)

    def test_sector_returns_project(self):
        self.assertEqual(self.sector._get_project(), self.project)

    def test_sector_authorization_returns_project(self):
        auth = SectorAuthorization.objects.create(
            sector=self.sector,
            permission=self.permission,
            role=SectorAuthorization.ROLE_MANAGER,
        )
        self.assertEqual(auth._get_project(), self.project)

    def test_sector_tag_returns_project(self):
        tag = SectorTag.objects.create(name="Tag GP", sector=self.sector)
        self.assertEqual(tag._get_project(), self.project)

    def test_sector_holiday_returns_project(self):
        holiday = SectorHoliday.objects.create(
            sector=self.sector,
            date=datetime.date(2025, 6, 12),
            day_type=SectorHoliday.CLOSED,
        )
        self.assertEqual(holiday._get_project(), self.project)

    def test_group_sector_returns_project(self):
        group = GroupSector.objects.create(
            name="GP Group", project=self.project, rooms_limit=5
        )
        self.assertEqual(group._get_project(), self.project)

    def test_queue_returns_project(self):
        self.assertEqual(self.queue._get_project(), self.project)

    def test_queue_authorization_returns_project(self):
        auth = QueueAuthorization.objects.create(
            queue=self.queue,
            permission=self.permission,
            role=QueueAuthorization.ROLE_AGENT,
        )
        self.assertEqual(auth._get_project(), self.project)

    def test_quick_message_with_sector_returns_project(self):
        qm = QuickMessage.objects.create(
            user=self.user,
            shortcut="/oi",
            text="Olá",
            sector=self.sector,
        )
        self.assertEqual(qm._get_project(), self.project)

    def test_quick_message_without_sector_raises_attribute_error(self):
        qm = QuickMessage.objects.create(
            user=self.user,
            shortcut="/oi2",
            text="Olá",
        )
        with self.assertRaises(AttributeError):
            qm._get_project()

    def test_model_without_project_raises_attribute_error(self):
        """Ensures AttributeError is raised for models without a project attribute."""
        from chats.core.models import AuditableMixin
        from django.db import models as dj_models

        class NoProjectModel(AuditableMixin):
            class Meta:
                app_label = "core"

        instance = NoProjectModel.__new__(NoProjectModel)
        with self.assertRaises(AttributeError):
            instance._get_project()
