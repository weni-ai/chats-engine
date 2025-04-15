import logging
from django.conf import settings
from chats.apps.queues.models import Queue
from chats.apps.queues.tasks import route_queue_rooms

logger = logging.getLogger(__name__)


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
