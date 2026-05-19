from datetime import time
from unittest.mock import patch
from django.test import TestCase

from chats.apps.projects.models.models import Project, RoomRoutingType
from chats.apps.queues.models import Queue
from chats.apps.queues.utils import (
    start_queue_priority_routing,
    start_queue_priority_routing_for_all_queues_in_project,
)
from chats.apps.sectors.models import Sector


class StartQueuePriorityRoutingTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start=time(hour=5, minute=0),
            work_end=time(hour=23, minute=59),
        )
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector,
        )

    @patch("chats.apps.queues.utils.logger")
    def test_start_queue_priority_routing_when_the_project_routing_type_is_not_queue_priority(
        self,
        mock_logger,
    ):

        self.project.room_routing_type = RoomRoutingType.GENERAL
        self.project.save()

        start_queue_priority_routing(self.queue)

        mock_logger.info.assert_any_call(
            "Skipping route_queue_rooms for queue %s because project is not configured to use priority routing",
            self.queue.uuid,
        )

    @patch("chats.apps.queues.utils.logger")
    @patch("chats.apps.queues.utils.route_queue_rooms")
    @patch("chats.apps.queues.utils.settings.USE_CELERY", False)
    def test_start_queue_priority_routing_when_celery_is_disabled(
        self,
        mock_route_queue_rooms,
        mock_logger,
    ):
        mock_route_queue_rooms.return_value = None

        start_queue_priority_routing(self.queue)

        mock_logger.info.assert_any_call(
            "Calling route_queue_rooms for queue %s synchronously because celery is disabled",
            self.queue.uuid,
        )

        mock_route_queue_rooms.assert_called_once_with(self.queue.uuid)

    @patch("chats.apps.queues.utils.logger")
    @patch("chats.apps.queues.utils.route_queue_rooms")
    @patch("chats.apps.queues.utils.settings.USE_CELERY", True)
    def test_start_queue_priority_routing_when_celery_is_enabled(
        self,
        mock_route_queue_rooms,
        mock_logger,
    ):
        mock_route_queue_rooms.delay.return_value = None

        start_queue_priority_routing(self.queue)

        mock_logger.info.assert_any_call(
            "Calling route_queue_rooms for queue %s asynchronously", self.queue.uuid
        )

        mock_route_queue_rooms.delay.assert_called_once_with(self.queue.uuid)


class StartQueuePriorityRoutingForAllQueuesInProjectTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            room_routing_type=RoomRoutingType.QUEUE_PRIORITY,
        )
        self.queues = []
        for i in range(3):
            sector = Sector.objects.create(
                name=f"Test Sector {i}",
                project=self.project,
                rooms_limit=1,
                work_start=time(hour=5, minute=0),
                work_end=time(hour=23, minute=59),
            )
            for j in range(2):
                queue = Queue.objects.create(
                    name=f"Test Queue {j}",
                    sector=sector,
                )
                self.queues.append(queue)

    @patch("chats.apps.queues.utils.route_sector_rooms")
    @patch("chats.apps.queues.utils.settings.USE_CELERY", False)
    def test_start_queue_priority_routing_for_all_queues_in_project(
        self,
        mock_route_sector_rooms,
    ):
        mock_route_sector_rooms.return_value = None

        start_queue_priority_routing_for_all_queues_in_project(self.project)

        sector_uuids_called = [
            c.args[0] for c in mock_route_sector_rooms.call_args_list
        ]
        expected_sector_uuids = list(
            Queue.objects.filter(sector__project=self.project)
            .values_list("sector__uuid", flat=True)
            .distinct()
        )
        self.assertEqual(sorted(sector_uuids_called), sorted(expected_sector_uuids))

    @patch("chats.apps.queues.utils.logger")
    @patch("chats.apps.queues.utils.route_queue_rooms")
    @patch("chats.apps.queues.utils.settings.USE_CELERY", False)
    def test_start_queue_priority_routing_for_all_queues_when_project_does_not_use_priority_routing(
        self,
        mock_route_queue_rooms,
        mock_logger,
    ):
        self.project.room_routing_type = RoomRoutingType.GENERAL
        self.project.save()

        mock_route_queue_rooms.return_value = None

        start_queue_priority_routing_for_all_queues_in_project(self.project)

        mock_logger.info.assert_any_call(
            "[start_queue_priority_routing_for_all_queues_in_project] Skipping routing for project %s "
            "because it is not configured to use priority routing",
            self.project.uuid,
        )

    @patch("chats.apps.queues.utils.route_sector_rooms")
    @patch("chats.apps.queues.utils.settings.USE_CELERY", False)
    def test_routes_by_sector_sync(
        self,
        mock_route_sector_rooms,
    ):
        mock_route_sector_rooms.return_value = None

        start_queue_priority_routing_for_all_queues_in_project(self.project)

        sector_uuids_called = [
            c.args[0] for c in mock_route_sector_rooms.call_args_list
        ]
        expected_sector_uuids = list(
            Queue.objects.filter(sector__project=self.project)
            .values_list("sector__uuid", flat=True)
            .distinct()
        )
        self.assertEqual(sorted(sector_uuids_called), sorted(expected_sector_uuids))

    @patch("chats.apps.queues.utils.route_sector_rooms")
    @patch("chats.apps.queues.utils.settings.USE_CELERY", True)
    def test_routes_by_sector_async(
        self,
        mock_route_sector_rooms,
    ):
        mock_route_sector_rooms.delay.return_value = None

        start_queue_priority_routing_for_all_queues_in_project(self.project)

        sector_uuids_called = [
            c.args[0] for c in mock_route_sector_rooms.delay.call_args_list
        ]
        expected_sector_uuids = list(
            Queue.objects.filter(sector__project=self.project)
            .values_list("sector__uuid", flat=True)
            .distinct()
        )
        self.assertEqual(sorted(sector_uuids_called), sorted(expected_sector_uuids))

    @patch("chats.apps.queues.utils.route_sector_rooms")
    @patch("chats.apps.queues.utils.route_queue_rooms")
    @patch("chats.apps.queues.utils.settings.USE_CELERY", False)
    def test_does_not_call_per_queue_routing(
        self,
        mock_route_queue_rooms,
        mock_route_sector_rooms,
    ):
        mock_route_sector_rooms.return_value = None

        start_queue_priority_routing_for_all_queues_in_project(self.project)

        mock_route_queue_rooms.assert_not_called()

    @patch("chats.apps.queues.utils.logger")
    @patch("chats.apps.queues.utils.route_sector_rooms")
    @patch("chats.apps.queues.utils.settings.USE_CELERY", False)
    def test_logs_sector_count(
        self,
        mock_route_sector_rooms,
        mock_logger,
    ):
        mock_route_sector_rooms.return_value = None

        start_queue_priority_routing_for_all_queues_in_project(self.project)

        mock_logger.info.assert_any_call(
            "[start_queue_priority_routing_for_all_queues_in_project] "
            "Started routing rooms by sector for project %s (%d sectors)",
            self.project.uuid,
            3,
        )
