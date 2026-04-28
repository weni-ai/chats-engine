import logging
from typing import TYPE_CHECKING

from django.conf import settings

from weni.feature_flags.shortcuts import is_feature_active_for_attributes

from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.queues.tasks import route_queue_rooms, route_sector_rooms
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.utils import create_transfer_json

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from chats.apps.rooms.models import Room
    from chats.apps.accounts.models import User


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

    When the cooldown feature flag is active, routes are grouped by sector
    so that all queues in a sector are routed under a single lock acquisition,
    preventing accidental queue prioritization.
    """
    if not project.use_queue_priority_routing:
        logger.info(
            "[start_queue_priority_routing_for_all_queues_in_project] Skipping routing for project %s "
            "because it is not configured to use priority routing",
            project.uuid,
        )
        return

    cooldown_feature_flag_active = is_feature_active_for_attributes(
        settings.ROUTE_QUEUE_COOLDOWN_FEATURE_FLAG_KEY,
        {"projectUUID": str(project.uuid)},
    )

    if cooldown_feature_flag_active:
        logger.info(
            "[start_queue_priority_routing_for_all_queues_in_project] "
            "Cooldown feature flag is active for project %s",
            project.uuid,
        )
        sector_uuids = (
            Queue.objects.filter(sector__project=project)
            .values_list("sector__uuid", flat=True)
            .distinct()
        )

        logger.info(
            "[start_queue_priority_routing_for_all_queues_in_project] "
            "Started routing rooms by sector for project %s (%d sectors)",
            project.uuid,
            len(sector_uuids),
        )

        for sector_uuid in sector_uuids:
            if settings.USE_CELERY:
                route_sector_rooms.delay(sector_uuid)
            else:
                route_sector_rooms(sector_uuid)
        return

    logger.info(
        "[start_queue_priority_routing_for_all_queues_in_project] "
        "Cooldown feature flag is not active for project %s",
        project.uuid,
    )

    queues = Queue.objects.filter(sector__project=project)

    logger.info(
        "[start_queue_priority_routing_for_all_queues_in_project] "
        "Started routing rooms for all queues in project %s",
        project.uuid,
    )

    for queue in queues:
        start_queue_priority_routing(queue)


def create_room_assigned_from_queue_feedback(room: "Room", user: "User"):
    """
    Create a feedback message for a room assigned from a queue.
    """
    from chats.apps.rooms.views import create_room_feedback_message

    feedback = create_transfer_json(
        action="auto_assign_from_queue",
        from_=room.queue,
        to=user,
    )

    create_room_feedback_message(
        room, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
    )
