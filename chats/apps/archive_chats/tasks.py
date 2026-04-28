import time
from datetime import datetime, timezone
from itertools import islice
from uuid import UUID

import logging

from celery import group, shared_task
from dateutil.relativedelta import relativedelta as rdelta
from django.conf import settings

from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.expiration import calculate_archive_task_expiration_dt
from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.archive_chats.services import ArchiveChatsService
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)


# TODO: Move to a dedicated "archive-chats-scheduler" queue
@shared_task(name="start_archive_rooms_messages")
def start_archive_rooms_messages():
    """
    This task is used to archive the messages of the rooms that were created more than 1 year ago.
    """
    logger.info("[start_archive_rooms_messages] Starting archive rooms messages")
    service = ArchiveChatsService()
    job = service.start_archive_job()
    logger.info(f"[start_archive_rooms_messages] Job created: {job.uuid}")

    now = datetime.now(timezone.utc)
    limit_date = now - rdelta(years=1)

    rooms_query = (
        Room.objects.filter(is_active=False, ended_at__lt=limit_date)
        .exclude(archived_conversations__status=ArchiveConversationsJobStatus.FINISHED)
        .exclude(archived_conversations__job__started_at__gte=now - rdelta(hours=24))
    )

    if not settings.ARCHIVE_CHATS_IS_ACTIVE_FOR_ALL_PROJECTS:
        logger.info(
            "[start_archive_rooms_messages] Not active for all projects, getting projects list from feature flag"
        )
        projects = service.get_projects()

        if len(projects) == 0 or not projects:
            logger.info(
                "[start_archive_rooms_messages] No projects found, skipping archive"
            )
            return

        rooms_query = rooms_query.filter(queue__sector__project__in=projects)

    room_uuids = list(
        rooms_query.order_by("ended_at").values_list("uuid", flat=True)[
            : settings.ARCHIVE_CHATS_MAX_ROOMS
        ]
    )
    rooms_count = len(room_uuids)

    expiration_dt = calculate_archive_task_expiration_dt(
        settings.ARCHIVE_CHATS_MAX_HOUR
    )

    logger.info(
        f"[start_archive_rooms_messages] Starting archive {rooms_count} rooms with job {job.uuid}"
    )
    logger.info(f"[start_archive_rooms_messages] Expiration date: {expiration_dt}")

    _create_pending_records(room_uuids, job)

    loop_start = time.monotonic()

    if settings.ARCHIVE_CHATS_USE_BATCH_DISPATCH:
        dispatched = _dispatch_batched(room_uuids, job.uuid, expiration_dt, rooms_count)
    else:
        dispatched = _dispatch_sequential(
            room_uuids, job.uuid, expiration_dt, rooms_count
        )

    loop_elapsed = time.monotonic() - loop_start

    logger.info(
        f"[start_archive_rooms_messages] Applied {dispatched} async tasks in {loop_elapsed:.2f}s"
    )


def _create_pending_records(room_uuids, job):
    """
    Bulk-create PENDING RoomArchivedConversation records at dispatch time so
    subsequent scheduler runs exclude already-queued rooms via the 24-hour
    job filter.
    """
    if not room_uuids:
        return

    new_room_ids = (
        Room.objects.filter(uuid__in=room_uuids)
        .exclude(archived_conversations__isnull=False)
        .values_list("uuid", flat=True)
    )

    if new_room_ids:
        RoomArchivedConversation.objects.bulk_create(
            [
                RoomArchivedConversation(
                    room_id=room_id,
                    job=job,
                    status=ArchiveConversationsJobStatus.PENDING,
                )
                for room_id in new_room_ids
            ],
            batch_size=settings.ARCHIVE_CHATS_BULK_CREATE_PENDING_BATCH_SIZE,
        )

    logger.info(f"[start_archive_rooms_messages] Created/updated {len(room_uuids)}")


def _dispatch_sequential(room_uuids, job_uuid, expiration_dt, rooms_count):
    dispatched = 0
    for room_uuid in room_uuids:
        archive_room_messages.apply_async(
            args=[room_uuid, job_uuid], expires=expiration_dt
        )
        dispatched += 1
        if dispatched % 1000 == 0:
            logger.info(
                f"[start_archive_rooms_messages] Dispatched {dispatched}/{rooms_count} tasks"
            )
    return dispatched


def _chunked(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk


def _dispatch_batched(room_uuids, job_uuid, expiration_dt, rooms_count):
    batch_size = settings.ARCHIVE_CHATS_BATCH_SIZE
    dispatched = 0
    for batch in _chunked(room_uuids, batch_size):
        sigs = [
            archive_room_messages.s(room_uuid, job_uuid).set(expires=expiration_dt)
            for room_uuid in batch
        ]
        group(sigs).apply_async()
        dispatched += len(batch)
        logger.info(
            f"[start_archive_rooms_messages] Dispatched {dispatched}/{rooms_count} tasks"
        )
    return dispatched


@shared_task(queue="archive-chats")
def archive_room_messages(room_uuid: UUID, job_uuid: UUID):
    logger.info(
        f"[archive_room_messages] Starting archive room messages for room {room_uuid} with job {job_uuid}"
    )
    try:
        job = ArchiveConversationsJob.objects.get(uuid=job_uuid)
    except ArchiveConversationsJob.DoesNotExist:
        logger.error(
            f"[archive_room_messages] Job {job_uuid} not found for room {room_uuid}"
        )
        return

    try:
        room = Room.objects.get(uuid=room_uuid)
    except Room.DoesNotExist:
        logger.error(
            f"[archive_room_messages] Room {room_uuid} not found for job {job_uuid}"
        )
        return

    logger.info(
        f"[archive_room_messages] Calling ArchiveChatsService "
        f"to archive room history for room {room_uuid} with job {job_uuid}"
    )

    service = ArchiveChatsService()
    service.archive_room_history(room, job)

    logger.info(
        f"[archive_room_messages] ArchiveChatsService "
        f"finished archiving room history for room {room_uuid} with job {job_uuid}"
    )
