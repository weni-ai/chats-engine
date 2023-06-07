from django.db import IntegrityError
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag


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

    def test_work_end_greater_than_work_start_check_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            Sector.objects.create(
                name="sector test",
                project=self.project,
                work_start="12",
                work_end="10",
                rooms_limit=10,
            )
        self.assertTrue(
            'new row for relation "sectors_sector" violates check constraint "wordend_greater_than_workstart_check"'
            in str(context.exception)
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
