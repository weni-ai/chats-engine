import logging
from typing import TYPE_CHECKING
from django.conf import settings
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.queues.tasks import route_queue_rooms
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.views import create_room_feedback_message, create_transfer_json

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from chats.apps.rooms.models import Room
    from chats.apps.users.models import User


def start_queue_priority_routing(queue: Queue):
    """
    Start routing rooms for a queue, if the project is configured to use priority routing.
    """

    if not queue.sector.project.use_queue_priority_routing:
        logger.info(
            "Skipping route_queue_rooms for queue %s because project is not configured to use priority routing",
            queue.uuid,
        )
        return

    if not settings.USE_CELERY:
        logger.info(
            "Calling route_queue_rooms for queue %s synchronously because celery is disabled",
            queue.uuid,
        )
        route_queue_rooms(queue.uuid)

        return

    logger.info("Calling route_queue_rooms for queue %s asynchronously", queue.uuid)
    route_queue_rooms.delay(queue.uuid)


def start_queue_priority_routing_for_all_queues_in_project(project: Project):
    """
    Start routing rooms for all queues in a project, if the project is configured to use priority routing.
    """
    if not project.use_queue_priority_routing:
        logger.info(
            "Skipping start_queue_priority_routing_for_all_queues_in_project for project %s "
            "because it is not configured to use priority routing",
            project.uuid,
        )
        return

    queues = Queue.objects.filter(sector__project=project)

    logger.info(
        "Started routing rooms for all queues in project %s",
        project.uuid,
    )

    for queue in queues:
        start_queue_priority_routing(queue)


def create_room_assigned_from_queue_feedback(room: "Room", user: "User"):
    """
    Create a feedback message for a room assigned from a queue.
    """
    feedback = create_transfer_json(
        action="auto_assign_from_queue",
        from_=room.queue,
        to=user,
    )

    create_room_feedback_message(
        room, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
    )
