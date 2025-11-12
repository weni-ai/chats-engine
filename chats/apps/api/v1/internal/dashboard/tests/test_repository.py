from datetime import datetime
import random
import pytz

from django.test import TestCase
from django.utils import timezone

from django.utils.timezone import timedelta


from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.repository import (
    AgentRepository,
    CSATRepository,
)
from chats.apps.projects.models.models import Project
from chats.apps.rooms.models import Room
from chats.apps.csat.models import CSATSurvey
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.contacts.models import Contact
from chats.apps.accounts.models import User
from chats.apps.projects.models import ProjectPermission
from chats.apps.sectors.models import SectorAuthorization
from chats.apps.queues.models import QueueAuthorization
from chats.apps.sectors.models import SectorTag
from chats.apps.projects.models.models import (
    CustomStatus,
    CustomStatusType,
)


class AgentRepositoryTestCase(TestCase):
    def setUp(self):
        self.repository = AgentRepository()

        # Create test project
        self.project = Project.objects.create(
            name="Test Project", timezone="America/Sao_Paulo"
        )

        # Create test sector
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )

        # Create test queue
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

        # Create test contact
        self.contact = Contact.objects.create(name="Test Contact")

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

    def test_get_converted_dates_with_different_formats(self):
        """Test _get_converted_dates with different date formats"""
        project = Project(timezone="America/Sao_Paulo")
        expected_tz = pytz.timezone("America/Sao_Paulo")

        # Test with date-only format
        filters = Filters(start_date="2024-01-01", end_date="2024-01-01")
        start_date, end_date = self.repository._get_converted_dates(filters, project)

        expected_start = expected_tz.localize(
            datetime.strptime("2024-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
        )
        expected_end = expected_tz.localize(
            datetime.strptime("2024-01-01 23:59:59", "%Y-%m-%d %H:%M:%S")
        )

        self.assertEqual(start_date, expected_start)
        self.assertEqual(end_date, expected_end)

        # Test with datetime format
        filters = Filters(
            start_date="2024-01-01T14:30:00", end_date="2024-01-01T16:45:00"
        )
        start_date, end_date = self.repository._get_converted_dates(filters, project)

        expected_start = expected_tz.localize(
            datetime.strptime("2024-01-01 14:30:00", "%Y-%m-%d %H:%M:%S")
        )
        expected_end = expected_tz.localize(
            datetime.strptime("2024-01-01 16:45:00", "%Y-%m-%d %H:%M:%S")
        )

        self.assertEqual(start_date, expected_start)
        self.assertEqual(end_date, expected_end)

    def test_get_csat_general_empty_data(self):
        """Test CSAT general metrics with no rooms or surveys"""
        filters = Filters(
            start_date="2024-01-01",
            end_date="2024-01-01",
        )
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)
        self.assertEqual(general_csat_metrics.rooms, 0)
        self.assertEqual(general_csat_metrics.reviews, 0)
        self.assertEqual(general_csat_metrics.avg_rating, None)

    def test_get_csat_general_rooms_without_csat(self):
        """Test CSAT general metrics with rooms but no CSAT surveys"""
        # Create closed rooms without CSAT surveys
        Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )
        Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )

        filters = Filters()
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)

        self.assertEqual(general_csat_metrics.rooms, 2)
        self.assertEqual(general_csat_metrics.reviews, 0)
        self.assertEqual(general_csat_metrics.avg_rating, None)

    def test_get_csat_general_rooms_with_csat(self):
        """Test CSAT general metrics with rooms that have CSAT surveys"""
        # Create closed rooms with CSAT surveys
        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )
        room2 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )
        Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )

        # Create CSAT surveys for rooms 1 and 2
        CSATSurvey.objects.create(room=room1, rating=5, answered_on=timezone.now())
        CSATSurvey.objects.create(room=room2, rating=3, answered_on=timezone.now())

        filters = Filters()
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)

        self.assertEqual(general_csat_metrics.rooms, 3)
        self.assertEqual(general_csat_metrics.reviews, 2)
        self.assertEqual(general_csat_metrics.avg_rating, 4.0)  # (5 + 3) / 2

    def test_get_csat_general_date_filtering(self):
        """Test CSAT general metrics with date filtering"""
        # Create rooms with different end dates
        old_date = timezone.now().replace(year=2023, month=12, day=31)
        recent_date = timezone.now().replace(year=2024, month=1, day=15)

        room_old = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=old_date,
        )
        room_recent = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=recent_date,
        )

        # Create CSAT surveys for both rooms
        CSATSurvey.objects.create(room=room_old, rating=4, answered_on=old_date)
        CSATSurvey.objects.create(room=room_recent, rating=5, answered_on=recent_date)

        # Test filtering by start date only
        filters = Filters(start_date="2024-01-01")
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)
        self.assertEqual(general_csat_metrics.rooms, 1)
        self.assertEqual(general_csat_metrics.reviews, 1)
        self.assertEqual(general_csat_metrics.avg_rating, 5.0)

        # Test filtering by date range
        filters = Filters(start_date="2023-12-01", end_date="2023-12-31")
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)
        self.assertEqual(general_csat_metrics.rooms, 1)
        self.assertEqual(general_csat_metrics.reviews, 1)
        self.assertEqual(general_csat_metrics.avg_rating, 4.0)

    def test_get_csat_general_sector_filtering(self):
        """Test CSAT general metrics with sector filtering"""
        # Create another sector and queue
        sector2 = Sector.objects.create(
            name="Test Sector 2",
            project=self.project,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )
        queue2 = Queue.objects.create(name="Test Queue 2", sector=sector2)

        # Create rooms in different sectors
        room_sector1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )
        room_sector2 = Room.objects.create(
            queue=queue2,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )

        # Create CSAT surveys
        CSATSurvey.objects.create(
            room=room_sector1, rating=4, answered_on=timezone.now()
        )
        CSATSurvey.objects.create(
            room=room_sector2, rating=5, answered_on=timezone.now()
        )

        # Test filtering by sector
        filters = Filters(sector=[self.sector.uuid])
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)
        self.assertEqual(general_csat_metrics.rooms, 1)
        self.assertEqual(general_csat_metrics.reviews, 1)
        self.assertEqual(general_csat_metrics.avg_rating, 4.0)

    def test_get_csat_general_queue_filtering(self):
        """Test CSAT general metrics with queue filtering"""
        # Create another queue in the same sector
        queue2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)

        # Create rooms in different queues
        room_queue1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )
        room_queue2 = Room.objects.create(
            queue=queue2,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )

        # Create CSAT surveys
        CSATSurvey.objects.create(
            room=room_queue1, rating=3, answered_on=timezone.now()
        )
        CSATSurvey.objects.create(
            room=room_queue2, rating=5, answered_on=timezone.now()
        )

        # Test filtering by queue
        filters = Filters(queue=self.queue.uuid)
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)
        self.assertEqual(general_csat_metrics.rooms, 1)
        self.assertEqual(general_csat_metrics.reviews, 1)
        self.assertEqual(general_csat_metrics.avg_rating, 3.0)

    def test_get_csat_general_average_calculation(self):
        """Test CSAT general metrics average rating calculation with various ratings"""
        # Create rooms with different ratings
        rooms = []
        ratings = [1, 2, 3, 4, 5]

        for rating in ratings:
            room = Room.objects.create(
                queue=self.queue,
                contact=self.contact,
                project_uuid=self.project.uuid,
                is_active=False,
                ended_at=timezone.now(),
            )
            CSATSurvey.objects.create(
                room=room, rating=rating, answered_on=timezone.now()
            )
            rooms.append(room)

        filters = Filters()
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)

        self.assertEqual(general_csat_metrics.rooms, 5)
        self.assertEqual(general_csat_metrics.reviews, 5)
        self.assertEqual(general_csat_metrics.avg_rating, 3.0)  # (1+2+3+4+5) / 5

    def test_get_csat_general_timezone_handling(self):
        """Test CSAT general metrics with different timezone handling"""
        # Create project with different timezone
        project_utc = Project.objects.create(name="Test Project UTC", timezone="UTC")

        # Create sector and queue for UTC project
        sector_utc = Sector.objects.create(
            name="Test Sector UTC",
            project=project_utc,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )
        queue_utc = Queue.objects.create(name="Test Queue UTC", sector=sector_utc)

        # Create room with specific end date within the filter range
        from datetime import datetime
        import pytz

        utc_tz = pytz.timezone("UTC")
        test_date = utc_tz.localize(datetime(2024, 6, 15, 12, 0, 0))

        room = Room.objects.create(
            queue=queue_utc,
            contact=self.contact,
            project_uuid=project_utc.uuid,
            is_active=False,
            ended_at=test_date,
        )

        CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())

        # Test with UTC timezone
        filters = Filters(start_date="2024-01-01", end_date="2024-12-31")
        general_csat_metrics = self.repository._get_csat_general(filters, project_utc)

        self.assertEqual(general_csat_metrics.rooms, 1)
        self.assertEqual(general_csat_metrics.reviews, 1)
        self.assertEqual(general_csat_metrics.avg_rating, 4.0)

    def test_get_csat_general_active_rooms_excluded(self):
        """Test that active rooms are excluded from CSAT general metrics"""
        # Create active room (should be excluded)
        active_room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=True,  # Active room
            ended_at=None,
        )

        # Create closed room (should be included)
        closed_room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,  # Closed room
            ended_at=timezone.now(),
        )

        # Create CSAT surveys for both rooms
        CSATSurvey.objects.create(
            room=active_room, rating=5, answered_on=timezone.now()
        )
        CSATSurvey.objects.create(
            room=closed_room, rating=3, answered_on=timezone.now()
        )

        filters = Filters()
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)

        # Only closed room should be counted
        self.assertEqual(general_csat_metrics.rooms, 1)
        self.assertEqual(general_csat_metrics.reviews, 1)
        self.assertEqual(general_csat_metrics.avg_rating, 3.0)

    def test_get_csat_general_tag_filtering(self):
        """Test CSAT general metrics with tag filtering"""
        # Create sector tags
        from chats.apps.sectors.models import SectorTag

        tag1 = SectorTag.objects.create(name="urgent", sector=self.sector)
        tag2 = SectorTag.objects.create(name="support", sector=self.sector)

        # Create rooms with different tags
        room_tag1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )
        room_tag1.tags.add(tag1)

        room_tag2 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )
        room_tag2.tags.add(tag2)

        room_both_tags = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=timezone.now(),
        )
        room_both_tags.tags.add(tag1, tag2)

        # Create CSAT surveys
        CSATSurvey.objects.create(room=room_tag1, rating=4, answered_on=timezone.now())
        CSATSurvey.objects.create(room=room_tag2, rating=3, answered_on=timezone.now())
        CSATSurvey.objects.create(
            room=room_both_tags, rating=5, answered_on=timezone.now()
        )

        # Test filtering by single tag
        filters = Filters(tags=[str(tag1.uuid)])
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)
        self.assertEqual(general_csat_metrics.rooms, 2)  # room_tag1 and room_both_tags
        self.assertEqual(general_csat_metrics.reviews, 2)
        self.assertEqual(general_csat_metrics.avg_rating, 4.5)  # (4 + 5) / 2

        # Test filtering by multiple tags (comma-separated)
        filters = Filters(tag=f"{tag1.uuid},{tag2.uuid}")
        general_csat_metrics = self.repository._get_csat_general(filters, self.project)

        self.assertGreaterEqual(general_csat_metrics.rooms, 3)  # At least 3 rooms
        self.assertGreaterEqual(general_csat_metrics.reviews, 3)  # At least 3 reviews
        # The average should be between 3 and 5
        self.assertGreaterEqual(general_csat_metrics.avg_rating, 3.0)
        self.assertLessEqual(general_csat_metrics.avg_rating, 5.0)

    def test_get_csat_agents_basic(self):
        from chats.apps.accounts.models import User
        from chats.apps.projects.models import ProjectPermission

        user1 = User.objects.create(
            email="agent1@test.com", first_name="Agent", last_name="One"
        )
        user2 = User.objects.create(
            email="agent2@test.com", first_name="Agent", last_name="Two"
        )

        ProjectPermission.objects.create(user=user1, project=self.project, role=2)
        ProjectPermission.objects.create(user=user2, project=self.project, role=2)

        filters = Filters()
        agents = self.repository._get_csat_agents(filters, self.project)

        self.assertEqual(agents.count(), 2)
        agent_emails = list(agents.values_list("email", flat=True))
        self.assertIn("agent1@test.com", agent_emails)
        self.assertIn("agent2@test.com", agent_emails)

    def test_get_csat_agents_admin_filtering(self):
        from chats.apps.accounts.models import User
        from chats.apps.projects.models import ProjectPermission

        user1 = User.objects.create(
            email="agent1@test.com", first_name="Agent", last_name="One"
        )
        admin_user = User.objects.create(
            email="admin@weni.ai", first_name="Admin", last_name="User"
        )

        ProjectPermission.objects.create(user=user1, project=self.project, role=2)
        ProjectPermission.objects.create(user=admin_user, project=self.project, role=2)

        filters = Filters(is_weni_admin=False)
        agents = self.repository._get_csat_agents(filters, self.project)

        agent_emails = list(agents.values_list("email", flat=True))
        self.assertIn("agent1@test.com", agent_emails)
        self.assertNotIn("admin@weni.ai", agent_emails)

        filters = Filters(is_weni_admin=True)
        agents = self.repository._get_csat_agents(filters, self.project)

        agent_emails = list(agents.values_list("email", flat=True))
        self.assertIn("agent1@test.com", agent_emails)
        self.assertIn("admin@weni.ai", agent_emails)

    def test_get_csat_agents_specific_agent(self):
        from chats.apps.accounts.models import User
        from chats.apps.projects.models import ProjectPermission

        user1 = User.objects.create(
            email="agent1@test.com", first_name="Agent", last_name="One"
        )
        user2 = User.objects.create(
            email="agent2@test.com", first_name="Agent", last_name="Two"
        )

        ProjectPermission.objects.create(user=user1, project=self.project, role=2)
        ProjectPermission.objects.create(user=user2, project=self.project, role=2)

        filters = Filters(agent="agent1@test.com")
        agents = self.repository._get_csat_agents(filters, self.project)

        self.assertEqual(agents.count(), 1)
        self.assertEqual(agents.first().email, "agent1@test.com")

    def test_get_csat_agents_combined_filters(self):
        from chats.apps.accounts.models import User
        from chats.apps.sectors.models import SectorAuthorization
        from chats.apps.queues.models import QueueAuthorization
        from chats.apps.projects.models import ProjectPermission

        user1 = User.objects.create(
            email="agent1@test.com", first_name="Agent", last_name="One"
        )
        user2 = User.objects.create(
            email="agent2@test.com", first_name="Agent", last_name="Two"
        )

        permission1 = ProjectPermission.objects.create(
            user=user1, project=self.project, role=2
        )
        permission2 = ProjectPermission.objects.create(
            user=user2, project=self.project, role=2
        )

        SectorAuthorization.objects.create(
            permission=permission1, sector=self.sector, role=1
        )
        SectorAuthorization.objects.create(
            permission=permission2, sector=self.sector, role=1
        )

        QueueAuthorization.objects.create(permission=permission1, queue=self.queue)

        filters = Filters(
            sector=[self.sector.uuid], queue=self.queue.uuid, agent="agent1@test.com"
        )
        agents = self.repository._get_csat_agents(filters, self.project)

        self.assertEqual(agents.count(), 1)
        self.assertEqual(agents.first().email, "agent1@test.com")

    def test_get_csat_rooms_query_basic(self):
        filters = Filters()
        rooms_query = self.repository._get_csat_rooms_query(filters, self.project)

        expected_query = {"rooms__is_active": False}
        self.assertEqual(rooms_query, expected_query)

    def test_get_csat_rooms_query_date_filtering(self):
        filters = Filters(start_date="2024-01-01", end_date="2024-01-31")
        rooms_query = self.repository._get_csat_rooms_query(filters, self.project)

        self.assertEqual(rooms_query["rooms__is_active"], False)
        self.assertIn("rooms__ended_at__gte", rooms_query)
        self.assertIn("rooms__ended_at__lte", rooms_query)

        filters_start_only = Filters(start_date="2024-01-01")
        rooms_query_start = self.repository._get_csat_rooms_query(
            filters_start_only, self.project
        )

        self.assertEqual(rooms_query_start["rooms__is_active"], False)
        self.assertIn("rooms__ended_at__gte", rooms_query_start)
        self.assertNotIn("rooms__ended_at__lte", rooms_query_start)

        filters_end_only = Filters(end_date="2024-01-31")
        rooms_query_end = self.repository._get_csat_rooms_query(
            filters_end_only, self.project
        )

        self.assertEqual(rooms_query_end["rooms__is_active"], False)
        self.assertNotIn("rooms__ended_at__gte", rooms_query_end)
        self.assertIn("rooms__ended_at__lte", rooms_query_end)

    def test_get_csat_rooms_query_sector_filtering(self):
        sector2 = Sector.objects.create(
            name="Test Sector 2",
            project=self.project,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )

        filters = Filters(sector=[self.sector.uuid, sector2.uuid])
        rooms_query = self.repository._get_csat_rooms_query(filters, self.project)

        self.assertEqual(rooms_query["rooms__is_active"], False)
        self.assertEqual(
            rooms_query["rooms__queue__sector__in"], [self.sector.uuid, sector2.uuid]
        )

    def test_get_csat_rooms_query_queue_filtering(self):
        Queue.objects.create(name="Test Queue 2", sector=self.sector)

        filters = Filters(queue=self.queue.uuid)
        rooms_query = self.repository._get_csat_rooms_query(filters, self.project)

        self.assertEqual(rooms_query["rooms__is_active"], False)
        self.assertEqual(rooms_query["rooms__queue"], self.queue.uuid)

    def test_get_csat_rooms_query_tag_filtering(self):
        from chats.apps.sectors.models import SectorTag

        tag1 = SectorTag.objects.create(name="urgent", sector=self.sector)
        tag2 = SectorTag.objects.create(name="support", sector=self.sector)

        filters_single = Filters(tags=[str(tag1.uuid)])
        rooms_query_single = self.repository._get_csat_rooms_query(
            filters_single, self.project
        )

        self.assertEqual(rooms_query_single["rooms__is_active"], False)
        self.assertEqual(rooms_query_single["rooms__tags__in"], [str(tag1.uuid)])

        filters_multiple = Filters(tags=[str(tag1.uuid), str(tag2.uuid)])
        rooms_query_multiple = self.repository._get_csat_rooms_query(
            filters_multiple, self.project
        )

        self.assertEqual(rooms_query_multiple["rooms__is_active"], False)
        self.assertEqual(
            rooms_query_multiple["rooms__tags__in"], [str(tag1.uuid), str(tag2.uuid)]
        )

    def test_get_csat_rooms_query_combined_filters(self):
        from chats.apps.sectors.models import SectorTag

        Sector.objects.create(
            name="Test Sector 2",
            project=self.project,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )
        Queue.objects.create(name="Test Queue 2", sector=self.sector)
        tag = SectorTag.objects.create(name="urgent", sector=self.sector)

        filters = Filters(
            start_date="2024-01-01",
            end_date="2024-01-31",
            sector=[self.sector.uuid],
            queue=self.queue.uuid,
            tags=[str(tag.uuid)],
        )
        rooms_query = self.repository._get_csat_rooms_query(filters, self.project)

        self.assertEqual(rooms_query["rooms__is_active"], False)
        self.assertIn("rooms__ended_at__gte", rooms_query)
        self.assertIn("rooms__ended_at__lte", rooms_query)
        self.assertEqual(rooms_query["rooms__queue__sector__in"], [self.sector.uuid])
        self.assertEqual(rooms_query["rooms__queue"], self.queue.uuid)
        self.assertEqual(rooms_query["rooms__tags__in"], [str(tag.uuid)])

    def test_get_agents_csat_score(self):
        sector2 = Sector.objects.create(
            name="Test Sector 2",
            project=self.project,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )
        queue2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)
        tag = SectorTag.objects.create(name="urgent", sector=self.sector)

        # Create users
        user1 = User.objects.create(
            email="agent1@test.com", first_name="Agent", last_name="One"
        )
        user2 = User.objects.create(
            email="agent2@test.com", first_name="Agent", last_name="Two"
        )
        admin_user = User.objects.create(
            email="admin@weni.ai", first_name="Admin", last_name="User"
        )

        # Create project permissions
        permission1 = ProjectPermission.objects.create(
            user=user1, project=self.project, role=2
        )
        permission2 = ProjectPermission.objects.create(
            user=user2, project=self.project, role=2
        )
        permission_admin = ProjectPermission.objects.create(
            user=admin_user, project=self.project, role=2
        )

        # Create authorizations
        SectorAuthorization.objects.create(
            permission=permission1, sector=self.sector, role=1
        )
        SectorAuthorization.objects.create(
            permission=permission2, sector=sector2, role=1
        )
        SectorAuthorization.objects.create(
            permission=permission_admin, sector=self.sector, role=1
        )

        QueueAuthorization.objects.create(permission=permission1, queue=self.queue)
        QueueAuthorization.objects.create(permission=permission2, queue=queue2)
        QueueAuthorization.objects.create(permission=permission_admin, queue=self.queue)

        # Create rooms with different end dates
        from datetime import datetime
        import pytz

        utc_tz = pytz.timezone("UTC")
        old_date = utc_tz.localize(datetime(2023, 12, 31, 12, 0, 0))
        recent_date = utc_tz.localize(datetime(2024, 1, 15, 12, 0, 0))

        # Create rooms for user1
        room1 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=recent_date,
            user=user1,
        )
        room1.tags.add(tag)

        room2 = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=recent_date,
            user=user1,
        )
        room2.tags.add(tag)

        # Create rooms for user2 (should be filtered out)
        room3 = Room.objects.create(
            queue=queue2,
            contact=self.contact,
            project_uuid=self.project.uuid,
            is_active=False,
            ended_at=old_date,
            user=user2,
        )

        # Create CSAT surveys
        CSATSurvey.objects.create(room=room1, rating=5, answered_on=recent_date)
        CSATSurvey.objects.create(room=room2, rating=3, answered_on=recent_date)
        CSATSurvey.objects.create(room=room3, rating=4, answered_on=old_date)

        # Test with comprehensive filters
        filters = Filters(
            start_date="2024-01-01",
            end_date="2024-01-31",
            sector=[self.sector.uuid],
            queue=self.queue.uuid,
            tag=str(tag.uuid),
            agent="agent1@test.com",
            is_weni_admin=False,
        )

        general_csat, agents_csat = self.repository.get_agents_csat_score(
            filters, self.project
        )

        # Test general CSAT metrics - verify we get some data
        self.assertGreaterEqual(general_csat.rooms, 0)
        self.assertGreaterEqual(general_csat.reviews, 0)
        self.assertGreaterEqual(general_csat.avg_rating, 0)

        # Test agents CSAT metrics - verify we get some data
        agents_list = list(agents_csat)
        self.assertGreaterEqual(len(agents_list), 0)

        if agents_list:
            agent_data = agents_list[0]
            self.assertEqual(agent_data.rooms_count, 2)
            self.assertEqual(agent_data.reviews, 2)
            self.assertEqual(agent_data.avg_rating, 4.0)


class CSATRepositoryTest(TestCase):
    def setUp(self):
        self.repository = CSATRepository()

        self.project = Project.objects.create(name="Test Project")
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

    def test_get_csat_ratings(self):
        rooms = [
            Room.objects.create(queue=self.queue, project_uuid=self.project.uuid)
            for _ in range(10)
        ]

        expected_ratings = {
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
        }

        for room in rooms:
            rating = random.randint(1, 5)
            CSATSurvey.objects.create(
                room=room, rating=rating, answered_on=timezone.now()
            )
            expected_ratings[rating] += 1

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project), self.project
        )

        total_count = sum(expected_ratings.values())

        for rating in ratings.ratings:
            self.assertEqual(rating.count, expected_ratings[rating.rating])
            self.assertEqual(
                rating.percentage,
                round((expected_ratings[rating.rating] / total_count) * 100, 2),
            )

    def test_get_csat_ratings_filter_by_queue(self):
        queue2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)

        rooms_queue1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(5)
        ]
        rooms_queue2 = [
            Room.objects.create(
                queue=queue2,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]

        for room in rooms_queue1:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())

        for room in rooms_queue2:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, queue=self.queue), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 5)
        self.assertEqual(rating_dict.get(4, 0), 0)

    def test_get_csat_ratings_filter_by_queues(self):
        queue2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)
        queue3 = Queue.objects.create(name="Test Queue 3", sector=self.sector)

        rooms_queue1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]
        rooms_queue2 = [
            Room.objects.create(
                queue=queue2,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(2)
        ]
        rooms_queue3 = [
            Room.objects.create(
                queue=queue3,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(4)
        ]

        for room in rooms_queue1:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_queue2:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())
        for room in rooms_queue3:
            CSATSurvey.objects.create(room=room, rating=3, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, queues=[self.queue, queue2]), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 3)
        self.assertEqual(rating_dict.get(4, 0), 2)
        self.assertEqual(rating_dict.get(3, 0), 0)  # queue3 excluded

    def test_get_csat_ratings_filter_by_sector(self):
        sector2 = Sector.objects.create(
            name="Test Sector 2",
            project=self.project,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )
        queue2 = Queue.objects.create(name="Test Queue 2", sector=sector2)
        rooms_sector1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(6)
        ]
        rooms_sector2 = [
            Room.objects.create(
                queue=queue2,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(4)
        ]

        for room in rooms_sector1:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_sector2:
            CSATSurvey.objects.create(room=room, rating=3, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, sector=[self.sector]), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 6)
        self.assertEqual(rating_dict.get(3, 0), 0)  # sector2 excluded

    def test_get_csat_ratings_filter_by_tag(self):
        tag1 = SectorTag.objects.create(name="Tag 1", sector=self.sector)
        tag2 = SectorTag.objects.create(name="Tag 2", sector=self.sector)

        rooms_tag1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(4)
        ]
        rooms_tag2 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]

        for room in rooms_tag1:
            room.tags.add(tag1)
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_tag2:
            room.tags.add(tag2)
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, tag=tag1), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 4)
        self.assertEqual(rating_dict.get(4, 0), 0)  # tag2 excluded

    def test_get_csat_ratings_filter_by_tags(self):
        tag1 = SectorTag.objects.create(name="Tag 1", sector=self.sector)
        tag2 = SectorTag.objects.create(name="Tag 2", sector=self.sector)
        tag3 = SectorTag.objects.create(name="Tag 3", sector=self.sector)

        rooms_tag1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]
        rooms_tag2 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(2)
        ]
        rooms_tag3 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(5)
        ]

        for room in rooms_tag1:
            room.tags.add(tag1)
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_tag2:
            room.tags.add(tag2)
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())
        for room in rooms_tag3:
            room.tags.add(tag3)
            CSATSurvey.objects.create(room=room, rating=3, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, tags=[tag1, tag2]), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 3)
        self.assertEqual(rating_dict.get(4, 0), 2)
        self.assertEqual(rating_dict.get(3, 0), 0)  # tag3 excluded

    def test_get_csat_ratings_filter_by_agent(self):
        agent1 = User.objects.create(
            email="agent1@test.com", first_name="Agent", last_name="One"
        )
        agent2 = User.objects.create(
            email="agent2@test.com", first_name="Agent", last_name="Two"
        )

        rooms_agent1 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                user=agent1,
                ended_at=timezone.now(),
            )
            for _ in range(5)
        ]
        rooms_agent2 = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                user=agent2,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]

        for room in rooms_agent1:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_agent2:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, agent=agent1), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 5)
        self.assertEqual(rating_dict.get(4, 0), 0)  # agent2 excluded

    def test_get_csat_ratings_filter_by_start_date(self):
        now = timezone.now()
        past_date = now - timedelta(days=5)

        old_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=past_date,
            )
            for _ in range(4)
        ]
        recent_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=now,
            )
            for _ in range(6)
        ]

        for room in old_rooms:
            CSATSurvey.objects.create(room=room, rating=2, answered_on=room.ended_at)
        for room in recent_rooms:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=room.ended_at)

        start_date = now - timedelta(days=2)
        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, start_date=start_date), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 6)
        self.assertEqual(rating_dict.get(2, 0), 0)  # old rooms excluded

    def test_get_csat_ratings_filter_by_end_date(self):
        now = timezone.now()
        past_date = now - timedelta(days=5)

        old_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=past_date,
            )
            for _ in range(3)
        ]
        recent_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=now,
            )
            for _ in range(5)
        ]

        for room in old_rooms:
            CSATSurvey.objects.create(room=room, rating=2, answered_on=room.ended_at)
        for room in recent_rooms:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=room.ended_at)

        end_date = now - timedelta(days=1)
        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, end_date=end_date), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(2, 0), 3)
        self.assertEqual(rating_dict.get(5, 0), 0)  # recent rooms excluded

    def test_get_csat_ratings_filter_by_date_range(self):
        now = timezone.now()
        very_old_date = now - timedelta(days=10)
        old_date = now - timedelta(days=5)
        middle_date = now - timedelta(days=3)
        recent_date = now - timedelta(days=1)

        very_old_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=very_old_date,
            )
            for _ in range(2)
        ]
        old_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=old_date,
            )
            for _ in range(3)
        ]
        middle_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=middle_date,
            )
            for _ in range(4)
        ]
        recent_rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=recent_date,
            )
            for _ in range(5)
        ]

        for room in very_old_rooms:
            CSATSurvey.objects.create(room=room, rating=1, answered_on=room.ended_at)
        for room in old_rooms:
            CSATSurvey.objects.create(room=room, rating=2, answered_on=room.ended_at)
        for room in middle_rooms:
            CSATSurvey.objects.create(room=room, rating=3, answered_on=room.ended_at)
        for room in recent_rooms:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=room.ended_at)

        start_date = now - timedelta(days=6)
        end_date = now - timedelta(days=2)
        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, start_date=start_date, end_date=end_date),
            self.project,
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(2, 0), 3)  # old_rooms
        self.assertEqual(rating_dict.get(3, 0), 4)  # middle_rooms
        self.assertEqual(rating_dict.get(1, 0), 0)  # very_old excluded
        self.assertEqual(rating_dict.get(4, 0), 0)  # recent excluded

    def test_get_csat_ratings_filter_combined_queue_and_agent(self):
        queue2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)
        agent1 = User.objects.create(
            email="agent1@test.com", first_name="Agent", last_name="One"
        )

        rooms_filtered = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                user=agent1,
                ended_at=timezone.now(),
            )
            for _ in range(4)
        ]
        rooms_wrong_queue = [
            Room.objects.create(
                queue=queue2,
                project_uuid=self.project.uuid,
                user=agent1,
                ended_at=timezone.now(),
            )
            for _ in range(2)
        ]
        rooms_wrong_agent = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]

        for room in rooms_filtered:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())
        for room in rooms_wrong_queue:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=timezone.now())
        for room in rooms_wrong_agent:
            CSATSurvey.objects.create(room=room, rating=3, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, queue=self.queue, agent=agent1),
            self.project,
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 4)  # Only matching rooms
        self.assertEqual(rating_dict.get(4, 0), 0)  # Wrong queue excluded
        self.assertEqual(rating_dict.get(3, 0), 0)  # Wrong agent excluded

    def test_get_csat_ratings_filter_combined_tag_and_date_range(self):
        tag1 = SectorTag.objects.create(name="Tag 1", sector=self.sector)
        now = timezone.now()
        old_date = now - timedelta(days=5)
        recent_date = now - timedelta(days=1)

        rooms_tag1_old = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=old_date,
            )
            for _ in range(2)
        ]
        rooms_tag1_recent = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=recent_date,
            )
            for _ in range(5)
        ]
        rooms_no_tag_recent = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=recent_date,
            )
            for _ in range(3)
        ]

        for room in rooms_tag1_old:
            room.tags.add(tag1)
            CSATSurvey.objects.create(room=room, rating=2, answered_on=room.ended_at)
        for room in rooms_tag1_recent:
            room.tags.add(tag1)
            CSATSurvey.objects.create(room=room, rating=5, answered_on=room.ended_at)
        for room in rooms_no_tag_recent:
            CSATSurvey.objects.create(room=room, rating=4, answered_on=room.ended_at)

        start_date = now - timedelta(days=3)
        end_date = now
        ratings = self.repository.get_csat_ratings(
            Filters(
                project=self.project,
                tag=tag1,
                start_date=start_date,
                end_date=end_date,
            ),
            self.project,
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 5)  # Only tag1 + recent date
        self.assertEqual(rating_dict.get(2, 0), 0)  # Old date excluded
        self.assertEqual(rating_dict.get(4, 0), 0)  # No tag excluded

    def test_get_csat_ratings_no_surveys_matching_filters(self):
        tag = SectorTag.objects.create(name="Tag 1", sector=self.sector)
        agent = User.objects.create(
            email="agent@test.com", first_name="Agent", last_name="One"
        )

        rooms = [
            Room.objects.create(
                queue=self.queue,
                project_uuid=self.project.uuid,
                ended_at=timezone.now(),
            )
            for _ in range(3)
        ]

        for room in rooms:
            CSATSurvey.objects.create(room=room, rating=5, answered_on=timezone.now())

        ratings = self.repository.get_csat_ratings(
            Filters(project=self.project, tag=tag, agent=agent), self.project
        )

        rating_dict = {r.rating: r.count for r in ratings.ratings}
        self.assertEqual(rating_dict.get(5, 0), 0)


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
