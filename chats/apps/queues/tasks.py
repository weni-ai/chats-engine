import logging
from uuid import UUID

from django.conf import settings
from django.core.cache import cache
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

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

    cooldown_feature_flag_active = is_feature_active_for_attributes(
        settings.ROUTE_QUEUE_COOLDOWN_FEATURE_FLAG_KEY,
        {"projectUUID": str(queue.sector.project.uuid)},
    )

    lock_key = f"route_queue_rooms_lock:{queue_uuid}"

    if cooldown_feature_flag_active:
        acquired = cache.add(
            lock_key, True, timeout=settings.ROUTE_QUEUE_COOLDOWN_MAX_TIME
        )
        if not acquired:
            logger.info("Route queue rooms cooldown is active for queue %s", queue.uuid)
            return False

    try:
        QueueRouterService(queue).route_rooms()
    finally:
        if cooldown_feature_flag_active:
            cache.delete(lock_key)

    return True
