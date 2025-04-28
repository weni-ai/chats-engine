from datetime import time
from unittest.mock import patch
from django.test import TestCase

from chats.apps.projects.models.models import Project, RoomRoutingType
from chats.apps.queues.models import Queue
from chats.apps.queues.utils import start_queue_priority_routing
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
