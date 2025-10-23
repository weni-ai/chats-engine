from datetime import datetime
from django.test import TestCase
from timezone_field.fields import pytz

from chats.apps.api.v1.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.repository import AgentRepository
from chats.apps.projects.models.models import Project


class AgentRepositoryTestCase(TestCase):
    def setUp(self):
        self.repository = AgentRepository()

    def test_get_converted_dates(self):
        filters = Filters(
            start_date="2024-01-01",
            end_date="2024-01-01",
        )
        project = Project(
            timezone="America/Sao_Paulo",
        )
        start_date, end_date = self.repository._get_converted_dates(filters, project)

        # Create expected datetime objects using the same method as the repository
        expected_tz = pytz.timezone("America/Sao_Paulo")
        expected_start = expected_tz.localize(
            datetime.strptime("2024-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
        )
        expected_end = expected_tz.localize(
            datetime.strptime("2024-01-01 23:59:59", "%Y-%m-%d %H:%M:%S")
        )

        self.assertEqual(start_date, expected_start)
        self.assertEqual(end_date, expected_end)
