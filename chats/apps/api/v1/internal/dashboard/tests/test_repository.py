import pytz
from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.repository import AgentRepository
from django.test import TestCase

from chats.apps.projects.models.models import (
    CustomStatus,
    CustomStatusType,
    Project,
    ProjectPermission,
)


class TestAgentRepository(TestCase):
    def setUp(self):
        self.repository = AgentRepository()

        self.project = Project.objects.create(
            name="Test Project",
            timezone=pytz.timezone("America/Sao_Paulo"),
            date_format=Project.DATE_FORMAT_DAY_FIRST,
            config={"agents_can_see_queue_history": True, "routing_option": None},
        )
        self.status_type = CustomStatusType.objects.create(
            name="Test Status",
            project=self.project,
        )

        self.users = [
            User.objects.create(
                email=f"agent{i}@test.com",
                first_name="Agent",
                last_name=f"Number {i}",
                is_active=True,
            )
            for i in range(2)
        ]

        ProjectPermission.objects.bulk_create(
            [
                ProjectPermission(
                    project=self.project,
                    user=user,
                    role=ProjectPermission.ROLE_ATTENDANT,
                    status=ProjectPermission.STATUS_ONLINE,
                )
                for user in self.users
            ]
        )

    def test_get_agents_custom_status(self):
        CustomStatus.objects.bulk_create(
            [
                CustomStatus(
                    project=self.project,
                    user=self.users[0],
                    status_type=self.status_type,
                    break_time=30,
                    is_active=False,
                )
                for i in range(2)
            ]
        )

        filters = Filters(
            queue=None,
            sector=None,
            tag=None,
            start_date=None,
            end_date=None,
            agent=None,
            is_weni_admin=False,
        )

        agents = self.repository.get_agents_custom_status(filters, self.project)

        self.assertEqual(agents.count(), 2)
        self.assertEqual(agents[0].time_with_status, 60)
        self.assertEqual(agents[1].time_with_status, 0)
