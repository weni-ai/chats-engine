import datetime

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector, SectorHoliday

# ---------------------------------------------------------------------------
# AuditableMixin — created_by / modified_by
# ---------------------------------------------------------------------------


class AuditableMixinCreateUpdateTests(TestCase):
    def setUp(self):
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
