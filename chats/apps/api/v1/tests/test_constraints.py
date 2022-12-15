from django.db import IntegrityError
from rest_framework.test import APITestCase

from chats.apps.projects.models import ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag


class ConstraintTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_sector.json']

    def setUp(self):
       self.project_permission = ProjectPermission.objects.get(uuid="e416fd45-2896-43a5-bd7a-5067f03c77fa")
       self.queue = Queue.objects.get(uuid="f2519480-7e58-4fc4-9894-9ab1769e29cf")
       self.queue_auth = QueueAuthorization.objects.get(uuid="3717f056-7ea5-4d38-80f5-ba907132807c")
       self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")
       self.sector = Sector.objects.get(uuid="21aecf8c-0c73-4059-ba82-4343e0cc627c")
       self.sector_auth = SectorAuthorization.objects.get(uuid="e87a90ed-f217-4655-9116-5c0b51203851")
       self.sector_tag = SectorTag.objects.get(uuid="62d9e7c4-4f2d-40fc-acf7-9549bface0fb")

    def test_unique_user_permission_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            project_permission = ProjectPermission.objects.create(
                user=self.project_permission.user, project=self.project_permission.project
            )
        self.assertTrue('duplicate key value violates unique constraint "unique_user_permission"' in str(context.exception))

    def test_unique_queue_name_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            queue = Queue.objects.create(
                name=self.queue.name, sector=self.queue.sector
            )
        self.assertTrue('duplicate key value violates unique constraint "unique_queue_name"' in str(context.exception))

    def test_unique_queue_auth_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            queue_auth = QueueAuthorization.objects.create(
                queue=self.queue_auth.queue, permission=self.queue_auth.permission
            )
        self.assertTrue('duplicate key value violates unique constraint "unique_queue_auth"' in str(context.exception))

    def test_unique_contact_queue_is_activetrue_room_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            room = Room.objects.create(
                contact=self.room.contact, queue=self.room.queue
            )
        self.assertTrue('duplicate key value violates unique constraint "unique_contact_queue_is_activetrue_room"' in str(context.exception))

    def test_wordend_greater_than_workstart_check_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            sector = Sector.objects.create(
              name="sector test", project=self.project_permission.project, work_start="12", work_end="10", rooms_limit=10
            )
        self.assertTrue('new row for relation "sectors_sector" violates check constraint "wordend_greater_than_workstart_check"' in str(context.exception))

    def test_unique_sector_name_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            sector = Sector.objects.create(
              name="Fluxos", project=self.sector.project, work_start="12", work_end="13", rooms_limit=10
            )
        self.assertTrue('duplicate key value violates unique constraint "unique_sector_name"' in str(context.exception))

    def test_rooms_limit_greater_than_zero_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            sector = Sector.objects.create(
              name="sector test 01", project=self.project_permission.project, work_start="12", work_end="13", rooms_limit=0
            )
        self.assertTrue('new row for relation "sectors_sector" violates check constraint "rooms_limit_greater_than_zero"' in str(context.exception))

    def test_unique_sector_auth_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            sector_authorization = SectorAuthorization.objects.create(
                permission=self.sector_auth.permission, sector=self.sector_auth.sector
            )
        self.assertTrue('duplicate key value violates unique constraint "unique_sector_auth"' in str(context.exception))

    def test_unique_tag_name_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            sector_tag = SectorTag.objects.create(
                name=self.sector_tag.name, sector=self.sector_tag.sector
            )
        self.assertTrue('duplicate key value violates unique constraint "unique_tag_name"' in str(context.exception))

    