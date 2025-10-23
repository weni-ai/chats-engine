from datetime import datetime
from django.test import TestCase
from django.utils import timezone
from timezone_field.fields import pytz

from chats.apps.api.v1.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.repository import AgentRepository
from chats.apps.projects.models.models import Project
from chats.apps.rooms.models import Room
from chats.apps.csat.models import CSATSurvey
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.contacts.models import Contact


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
        filters = Filters(tag=str(tag1.uuid))
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

    def test_get_csat_agents_sector_filtering(self):
        from chats.apps.accounts.models import User
        from chats.apps.sectors.models import SectorAuthorization
        from chats.apps.projects.models import ProjectPermission

        sector2 = Sector.objects.create(
            name="Test Sector 2",
            project=self.project,
            rooms_limit=10,
            work_start="00:00",
            work_end="23:59",
        )

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
            permission=permission2, sector=sector2, role=1
        )

        filters = Filters(sector=[self.sector.uuid])
        agents = self.repository._get_csat_agents(filters, self.project)

        self.assertEqual(agents.count(), 1)
        self.assertEqual(agents.first().email, "agent1@test.com")

    def test_get_csat_agents_queue_filtering(self):
        from chats.apps.accounts.models import User
        from chats.apps.queues.models import QueueAuthorization
        from chats.apps.projects.models import ProjectPermission

        queue2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)

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

        QueueAuthorization.objects.create(permission=permission1, queue=self.queue)
        QueueAuthorization.objects.create(permission=permission2, queue=queue2)

        filters = Filters(queue=self.queue.uuid)
        agents = self.repository._get_csat_agents(filters, self.project)

        self.assertEqual(agents.count(), 1)
        self.assertEqual(agents.first().email, "agent1@test.com")

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

        expected_query = {"is_active": False}
        self.assertEqual(rooms_query, expected_query)

    def test_get_csat_rooms_query_date_filtering(self):
        filters = Filters(start_date="2024-01-01", end_date="2024-01-31")
        rooms_query = self.repository._get_csat_rooms_query(filters, self.project)

        self.assertEqual(rooms_query["is_active"], False)
        self.assertIn("rooms__ended_at__gte", rooms_query)
        self.assertIn("rooms__ended_at__lte", rooms_query)

        filters_start_only = Filters(start_date="2024-01-01")
        rooms_query_start = self.repository._get_csat_rooms_query(
            filters_start_only, self.project
        )

        self.assertEqual(rooms_query_start["is_active"], False)
        self.assertIn("rooms__ended_at__gte", rooms_query_start)
        self.assertNotIn("rooms__ended_at__lte", rooms_query_start)

        filters_end_only = Filters(end_date="2024-01-31")
        rooms_query_end = self.repository._get_csat_rooms_query(
            filters_end_only, self.project
        )

        self.assertEqual(rooms_query_end["is_active"], False)
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

        self.assertEqual(rooms_query["is_active"], False)
        self.assertEqual(
            rooms_query["rooms__queue__sector__in"], [self.sector.uuid, sector2.uuid]
        )

    def test_get_csat_rooms_query_queue_filtering(self):
        Queue.objects.create(name="Test Queue 2", sector=self.sector)

        filters = Filters(queue=self.queue.uuid)
        rooms_query = self.repository._get_csat_rooms_query(filters, self.project)

        self.assertEqual(rooms_query["is_active"], False)
        self.assertEqual(rooms_query["rooms__queue"], self.queue.uuid)

    def test_get_csat_rooms_query_tag_filtering(self):
        from chats.apps.sectors.models import SectorTag

        tag1 = SectorTag.objects.create(name="urgent", sector=self.sector)
        tag2 = SectorTag.objects.create(name="support", sector=self.sector)

        filters_single = Filters(tag=str(tag1.uuid))
        rooms_query_single = self.repository._get_csat_rooms_query(
            filters_single, self.project
        )

        self.assertEqual(rooms_query_single["is_active"], False)
        self.assertEqual(rooms_query_single["rooms__tags__in"], [str(tag1.uuid)])

        filters_multiple = Filters(tag=f"{tag1.uuid},{tag2.uuid}")
        rooms_query_multiple = self.repository._get_csat_rooms_query(
            filters_multiple, self.project
        )

        self.assertEqual(rooms_query_multiple["is_active"], False)
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
            tag=str(tag.uuid),
        )
        rooms_query = self.repository._get_csat_rooms_query(filters, self.project)

        self.assertEqual(rooms_query["is_active"], False)
        self.assertIn("rooms__ended_at__gte", rooms_query)
        self.assertIn("rooms__ended_at__lte", rooms_query)
        self.assertEqual(rooms_query["rooms__queue__sector__in"], [self.sector.uuid])
        self.assertEqual(rooms_query["rooms__queue"], self.queue.uuid)
        self.assertEqual(rooms_query["rooms__tags__in"], [str(tag.uuid)])
