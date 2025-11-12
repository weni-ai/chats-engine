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
        self.in_service_status_type = CustomStatusType.objects.create(
            name="In-Service",
            project=self.project,
        )
        self.status_types = CustomStatusType.objects.bulk_create(
            [
                CustomStatusType(
                    name=f"Test Status {i}",
                    project=self.project,
                )
                for i in range(2)
            ]
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
        for status_type in self.status_types:
            CustomStatus.objects.bulk_create(
                [
                    CustomStatus(
                        project=self.project,
                        user=self.users[0],
                        status_type=status_type,
                        break_time=30,
                        is_active=False,
                    )
                    for i in range(2)
                ]
            )

        self.in_service_status = CustomStatus.objects.create(
            project=self.project,
            user=self.users[0],
            status_type=self.in_service_status_type,
            break_time=30,
            is_active=False,
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
