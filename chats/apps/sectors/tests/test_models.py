from datetime import date, datetime, time
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models.models import Project, RoomRoutingType
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import (
    Sector,
    SectorAuthorization,
    SectorHoliday,
    SectorTag,
)
from chats.apps.sectors.utils import WorkingHoursValidator


class ConstraintTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.sector = Sector.objects.get(uuid="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.project = self.sector.project
        self.sector_auth = SectorAuthorization.objects.get(
            uuid="e87a90ed-f217-4655-9116-5c0b51203851"
        )
        self.sector_tag = SectorTag.objects.get(
            uuid="62d9e7c4-4f2d-40fc-acf7-9549bface0fb"
        )

    def test_unique_sector_name_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            Sector.objects.create(
                name="Fluxos",
                project=self.sector.project,
                work_start="12",
                work_end="13",
                rooms_limit=10,
            )
        self.assertTrue(
            'duplicate key value violates unique constraint "unique_sector_name"'
            in str(context.exception)
        )

    def test_unique_sector_auth_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            SectorAuthorization.objects.create(
                permission=self.sector_auth.permission, sector=self.sector_auth.sector
            )
        self.assertTrue(
            'duplicate key value violates unique constraint "unique_sector_auth"'
            in str(context.exception)
        )

    def test_unique_tag_name_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            SectorTag.objects.create(
                name=self.sector_tag.name, sector=self.sector_tag.sector
            )
        self.assertTrue(
            'duplicate key value violates unique constraint "unique_tag_name"'
            in str(context.exception)
        )


class PropertyTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.sector = Sector.objects.get(uuid="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.project = self.sector.project
        self.sector_auth = SectorAuthorization.objects.get(
            uuid="00185928-ef97-47b8-9295-5462ff797a4e"
        )
        self.sector_tag = SectorTag.objects.get(
            uuid="62d9e7c4-4f2d-40fc-acf7-9549bface0fb"
        )
        self.sector_rooms = Room.objects.get(queue__sector=self.sector)
        self.permission_user = User.objects.get(email=self.sector_auth.permission.user)

    def test_name_property(self):
        """
        Verify if the property for get sector name its returning the correct value.
        """
        self.assertEqual(self.sector.sector, self.sector)

    def test_manager_auth(self):
        """
        Verify if the property for get manager authorizations its returning the correct value.
        """
        permission_returned = self.sector.manager_authorizations
        self.assertTrue(self.sector_auth in permission_returned)

    def test_employee_pks(self):
        """
        Verify if the property for get employee_pks its returning the correct value.
        """
        self.assertTrue(self.sector.employee_pks, self.sector_auth.permission.user.pk)

    def test_rooms(self):
        """
        Verify if the property for get rooms from sector its returning the correct value.
        """
        self.assertTrue(self.sector_rooms, self.sector.rooms)

    def test_active_chats(self):
        """
        Verify if the property for get active rooms from sector its returning the correct value.
        """
        self.assertTrue(self.sector.active_rooms, self.sector.rooms)

    def test_deactive_chats(self):
        """
        Verify if the property for get active rooms from sector its returning the correct value.
        """
        self.assertFalse(self.sector.deactivated_rooms, self.sector.rooms)

    def test_open_active_rooms(self):
        """
        Verify if the property for get active rooms from sector its returning the correct value.
        """
        self.assertFalse(self.sector.open_active_rooms, self.sector.rooms)

    def test_closed_active_rooms(self):
        """
        Verify if the property for get active rooms from sector its returning the correct value.
        """
        self.assertTrue(self.sector.closed_active_rooms, self.sector.rooms)

    def test_open_deactivated_rooms(self):
        """
        Verify if the property for get active rooms from sector its returning the correct value.
        """
        self.assertFalse(self.sector.open_deactivated_rooms, self.sector.rooms)

    def test_vacant_deactivated_rooms(self):
        """
        Verify if the property for get active rooms from sector its returning the correct value.
        """
        self.assertFalse(self.sector.vacant_deactivated_rooms, self.sector.rooms)

    def test_agent_count(self):
        """
        Verify if the property for get active rooms from sector its returning the correct value.
        """
        self.assertTrue(self.sector.agent_count, 1)

    def test_is_manager(self):
        """
        Verify if the property for get active rooms from sector its returning the correct value.
        """
        self.assertTrue(self.sector_auth.is_manager, True)

    def test_is_authorized(self):
        """
        Verify if the property for get active rooms from sector its returning the correct value.
        """
        self.assertTrue(self.sector_auth.is_authorized, True)

    def test_can_edit(self):
        """
        Verify if the property for get active rooms from sector its returning the correct value.
        """
        self.assertTrue(self.sector_auth.can_edit, True)

    def test_get_permission(self):
        """
        Verify if the property for get permissions its returning the correct value.
        """
        permission_returned = self.sector_auth.get_permission(
            self.sector_auth.permission.user
        )
        self.assertTrue(self.sector_auth.permission.pk, permission_returned.pk)


class TestSectorSave(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )

    @patch("chats.apps.sectors.models.start_queue_priority_routing")
    @patch("chats.apps.sectors.models.logger")
    def test_start_queue_priority_routing_when_rooms_limit_is_increased(
        self,
        mock_logger,
        mock_start_queue_priority_routing,
    ):
        mock_start_queue_priority_routing.return_value = None

        self.sector.rooms_limit = 2
        self.sector.save()

        mock_start_queue_priority_routing.assert_called_once_with(self.queue)

        mock_logger.info.assert_called_once_with(
            "Rooms limit increased for sector %s (%s), triggering queue priority routing",
            self.sector.name,
            self.sector.pk,
        )

    @patch("chats.apps.sectors.models.start_queue_priority_routing")
    def test_start_queue_priority_routing_when_rooms_limit_is_decreased(
        self,
        mock_start_queue_priority_routing,
    ):
        self.sector.rooms_limit = 0
        self.sector.save()

        mock_start_queue_priority_routing.assert_not_called()

    @patch("chats.apps.sectors.models.start_queue_priority_routing")
    def test_start_queue_priority_routing_when_rooms_limit_is_not_changed(
        self,
        mock_start_queue_priority_routing,
    ):
        self.sector.save()

        mock_start_queue_priority_routing.assert_not_called()


class SectorHolidaySoftDeleteUniquenessTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Holidays Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Support",
            project=self.project,
            rooms_limit=1,
        )
        self.holiday_date = date(2025, 1, 6)  # Monday

    def test_recreate_after_soft_delete_should_not_violate_uniqueness(self):
        first = SectorHoliday.objects.create(
            sector=self.sector,
            date=self.holiday_date,
            day_type=SectorHoliday.CLOSED,
            description="Test",
        )
        first.is_deleted = True
        first.save(update_fields=["is_deleted"])

        try:
            SectorHoliday.objects.create(
                sector=self.sector,
                date=self.holiday_date,
                day_type=SectorHoliday.CLOSED,
                description="Recreated",
            )
        except IntegrityError:
            self.fail(
                "Should allow recreating holiday after soft delete (uniqueness must ignore is_deleted=True)."
            )


class _FakeCache:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key, None)

    def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    def delete(self, key):
        self.store.pop(key, None)
        return True


class SectorHolidayCacheInvalidationTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Cache Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Sales",
            project=self.project,
            rooms_limit=1,
            working_day={
                "working_hours": {
                    "closed_weekdays": [],
                    "schedules": {
                        "monday": {"start": "08:00", "end": "17:00"},
                        "tuesday": {"start": "08:00", "end": "17:00"},
                        "wednesday": {"start": "08:00", "end": "17:00"},
                        "thursday": {"start": "08:00", "end": "17:00"},
                        "friday": {"start": "08:00", "end": "17:00"},
                    },
                }
            },
        )
        self.monday_dt = datetime(2025, 1, 6, 9, 0, 0)  # Monday 09:00
        self.cache = _FakeCache()
        self.validator = WorkingHoursValidator()

    @patch("chats.apps.sectors.utils.CacheClient")
    def test_cache_is_invalidated_on_create(self, MockCacheClient):
        MockCacheClient.return_value = self.cache
        cache_key = f"holiday:{self.sector.uuid}:{self.monday_dt.date()}"

        # Prime cache com "null" (sem feriado)
        self.cache.set(cache_key, "null", ex=300)

        # Primeiro check: sem feriado -> deve passar
        self.validator.validate_working_hours(self.sector, self.monday_dt)

        # Cria feriado (fechado) para a mesma data
        SectorHoliday.objects.create(
            sector=self.sector,
            date=self.monday_dt.date(),
            day_type=SectorHoliday.CLOSED,
            description="New Holiday",
        )

        # Esperado: invalidação de cache -> agora deve lançar
        with self.assertRaises(ValidationError):
            self.validator.validate_working_hours(self.sector, self.monday_dt)

    @patch("chats.apps.sectors.utils.CacheClient")
    def test_cache_is_invalidated_on_delete(self, MockCacheClient):
        MockCacheClient.return_value = self.cache
        cache_key = f"holiday:{self.sector.uuid}:{self.monday_dt.date()}"

        # Cria feriado e popula cache executando a validação uma vez
        holiday = SectorHoliday.objects.create(
            sector=self.sector,
            date=self.monday_dt.date(),
            day_type=SectorHoliday.CLOSED,
            description="Existing Holiday",
        )
        # Este check deve lançar e também setar o cache
        with self.assertRaises(ValidationError):
            self.validator.validate_working_hours(self.sector, self.monday_dt)
        self.assertIn(cache_key, self.cache.store)

        # Soft delete
        holiday.is_deleted = True
        holiday.save(update_fields=["is_deleted"])

        # Esperado: invalidação -> agora deve passar (sem feriado)
        self.validator.validate_working_hours(self.sector, self.monday_dt)


class SectorRequiredTagsTests(TransactionTestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Required Tags Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Required Tags Sector",
            project=self.project,
            required_tags=True,
            rooms_limit=1,
        )
        self.sector_tag = SectorTag.objects.create(
            name="Required Tags Tag",
            sector=self.sector,
        )

    def test_disable_required_tags_when_tag_is_deleted(self):
        self.assertTrue(self.sector.required_tags)

        self.sector_tag.delete()
        self.sector.refresh_from_db()

        self.assertFalse(self.sector.required_tags)
