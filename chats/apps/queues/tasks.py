import logging
from uuid import UUID


from chats.apps.queues.models import Queue
from chats.apps.queues.services import QueueRouterService
from chats.celery import app


logger = logging.getLogger(__name__)


@app.task
def route_queue_rooms(queue_uuid: UUID):
    """
    Route rooms to available agents for a queue in a project
    configured to use queue priority routing.
    """
    queue = Queue.objects.filter(uuid=queue_uuid).first()

    if not queue:
        logger.info("Queue not found for UUID: %s", queue_uuid)
        return

    QueueRouterService(queue).route_rooms()
