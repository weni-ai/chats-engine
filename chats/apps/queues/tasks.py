import logging
from uuid import UUID

from django.conf import settings
from django.core.cache import cache
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

from chats.apps.queues.models import Queue
from chats.apps.queues.services import QueueRouterService
from chats.celery import app


logger = logging.getLogger(__name__)


def get_route_lock_key_for_sector(sector_uuid: UUID):
    return f"route_queue_rooms_lock:{sector_uuid}"


def get_route_lock_key_for_queue(queue_uuid: UUID):
    return f"route_queue_rooms_lock:{queue_uuid}"


def get_route_pending_key_for_queue(queue_uuid: UUID):
    return f"route_queue_rooms_pending:{queue_uuid}"


def get_route_pending_key_for_sector(sector_uuid: UUID):
    return f"route_sector_rooms_pending:{sector_uuid}"


@app.task
def route_queue_rooms(queue_uuid: UUID):
    """
    Route rooms to available agents for a queue in a project
    configured to use queue priority routing.
    """
    queue = Queue.objects.filter(uuid=queue_uuid).first()
    if not queue:
        logger.info("[route_queue_rooms] Queue not found for UUID: %s", queue_uuid)
        return
    cooldown_feature_flag_active = is_feature_active_for_attributes(
        settings.ROUTE_QUEUE_COOLDOWN_FEATURE_FLAG_KEY,
        {"projectUUID": str(queue.sector.project.uuid)},
    )
    lock_key = get_route_lock_key_for_queue(queue.uuid)
    pending_key = get_route_pending_key_for_queue(queue_uuid)
    if cooldown_feature_flag_active:
        acquired = cache.add(
            lock_key, True, timeout=settings.ROUTE_QUEUE_COOLDOWN_MAX_TIME
        )
        if not acquired:
            logger.info(
                "[route_queue_rooms] Route queue rooms cooldown is active for queue %s. "
                "Skipping routing for now.",
                queue.uuid,
            )
            already_pending = not cache.add(
                pending_key, True, timeout=settings.ROUTE_QUEUE_COOLDOWN_RETRY_DELAY
            )
            if not already_pending:
                route_queue_rooms.apply_async(
                    args=[queue_uuid],
                    countdown=settings.ROUTE_QUEUE_COOLDOWN_RETRY_DELAY,
                )
                logger.info(
                    "[route_queue_rooms] Scheduled deferred route_queue_rooms for queue %s",
                    queue.uuid,
                )
            return False
    try:
        QueueRouterService(queue).route_rooms()
    finally:
        if cooldown_feature_flag_active:
            cache.delete(lock_key)
    return True


@app.task
def route_sector_rooms(sector_uuid: UUID):
    """
    Route rooms for all queues in a sector under a single lock acquisition,
    preventing accidental queue prioritization that occurs when individual
    route_queue_rooms tasks compete for the same sector lock.
    """
    from chats.apps.sectors.models import Sector

    sector = Sector.objects.filter(uuid=sector_uuid).first()
    if not sector:
        logger.info("[route_sector_rooms] Sector not found for UUID: %s", sector_uuid)
        return

    lock_key = get_route_lock_key_for_sector(sector_uuid)
    pending_key = get_route_pending_key_for_sector(sector_uuid)

    acquired = cache.add(lock_key, True, timeout=settings.ROUTE_QUEUE_COOLDOWN_MAX_TIME)
    if not acquired:
        logger.info(
            "[route_sector_rooms] Route sector rooms cooldown is active for sector %s. "
            "Skipping routing for now.",
            sector_uuid,
        )
        already_pending = not cache.add(
            pending_key, True, timeout=settings.ROUTE_QUEUE_COOLDOWN_RETRY_DELAY
        )
        if not already_pending:
            route_sector_rooms.apply_async(
                args=[sector_uuid],
                countdown=settings.ROUTE_QUEUE_COOLDOWN_RETRY_DELAY,
            )
            logger.info(
                "[route_sector_rooms] Scheduled deferred route_sector_rooms for sector %s",
                sector_uuid,
            )
        return False

    try:
        queues = Queue.objects.filter(sector=sector)
        for queue in queues:
            try:
                QueueRouterService(queue).route_rooms()
            except ValueError:
                logger.info(
                    "[route_sector_rooms] Skipping queue %s: priority routing not enabled",
                    queue.uuid,
                )
    finally:
        cache.delete(lock_key)
    return True
