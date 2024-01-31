from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.dto import Filters
from chats.apps.api.v1.dashboard.service import RawDataService
from chats.apps.projects.models import Project
from chats.apps.projects.models.models import ProjectPermission


class RedisMock:
    cache = {}

    def set(self, key, value):
        self.cache[key] = value

    def get(self, key):
        return self.cache[key]


class ServiceTests(TestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.user = User.objects.get(pk="8")

    def test_active_chats_function_passing_sector(self):
        project = self.project
        user_permission = ProjectPermission.objects.get(user=self.user, project=project)
        filters = Filters(
            sector="d49049f0-c601-4e05-a293-98c1dea5fe4f",
            user_request=user_permission,
            project=project,
            is_weni_admin=True if self.user and "weni.ai" in self.user.email else False,
        )
        raw_service = RawDataService()
        raw_data_count = raw_service.get_raw_data(filters)
        self.assertEqual(raw_data_count["raw_data"][0]["active_rooms"], 0)

    def test_active_chats_function_without_filter(self):
        project = self.project
        user_permission = ProjectPermission.objects.get(user=self.user, project=project)
        filters = Filters(
            user_request=user_permission,
            project=project,
            is_weni_admin=True if self.user and "weni.ai" in self.user.email else False,
        )
        raw_service = RawDataService()
        raw_data_count = raw_service.get_raw_data(filters)
        self.assertEqual(raw_data_count["raw_data"][0]["active_rooms"], 1)
