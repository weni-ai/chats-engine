from django.db import IntegrityError
from rest_framework.test import APITestCase

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

    def test_rooms_limit_greater_than_zero_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            Sector.objects.create(
                name="sector test 01",
                project=self.project,
                work_start="12",
                work_end="13",
                rooms_limit=0,
            )
        self.assertTrue(
            'new row for relation "sectors_sector" violates check constraint "rooms_limit_greater_than_zero"'
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
