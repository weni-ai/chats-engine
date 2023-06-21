from unittest.mock import patch

from django.test import TestCase

from chats.apps.api.v1.dashboard.serializers import DashboardRoomsSerializer
from chats.apps.projects.models import Project


class RedisMock:
    cache = {}

    def set(self, key, value):
        self.cache[key] = value

    def get(self, key):
        return self.cache[key]


class SerializerTests(TestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")

    @patch("chats.apps.api.v1.dashboard.serializers.get_redis_connection")
    def test_init_function(self, mock):
        """
        Verify if the init function its working properly.
        """
        mock.return_value = RedisMock()
        serializer = DashboardRoomsSerializer()
        self.assertTrue(isinstance(serializer.redis_connection, RedisMock))

    def test_active_chats_function_passing_sector(self):
        serializer = DashboardRoomsSerializer.get_active_chats(
            self=DashboardRoomsSerializer(
                context={
                    "sector": "d49049f0-c601-4e05-a293-98c1dea5fe4f",
                }
            ),
            project=self.project,
        )
        self.assertEqual(serializer, 0)

    def test_active_chats_function_without_filter(self):
        serializer = DashboardRoomsSerializer.get_active_chats(
            self=DashboardRoomsSerializer(context={}),
            project=self.project,
        )
        self.assertEqual(serializer, 1)
