from datetime import datetime, timezone
from uuid import UUID
from celery import shared_task
from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.expiration import calculate_archive_task_expiration_dt
from chats.apps.projects.models.models import Room
from django.conf import settings
import logging
from dateutil.relativedelta import relativedelta as rdelta


from chats.apps.archive_chats.models import ArchiveConversationsJob
from chats.apps.archive_chats.services import ArchiveChatsService

logger = logging.getLogger(__name__)


@shared_task(queue="archive_chats")
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

    rooms = (
        Room.objects.filter(is_active=False, ended_at__lt=limit_date)
        .exclude(archived_conversations__status=ArchiveConversationsJobStatus.FINISHED)
        .order_by("ended_at")[: settings.ARCHIVE_CHATS_MAX_ROOMS]
    )

    expiration_dt = calculate_archive_task_expiration_dt(
        settings.ARCHIVE_CHATS_MAX_HOUR
    )

    for room in rooms:
        archive_room_messages.apply_async(
            args=[room.uuid, job.uuid], expires=expiration_dt
        )


@shared_task(queue="archive_chats")
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
