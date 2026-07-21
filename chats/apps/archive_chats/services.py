from abc import ABC, abstractmethod
from datetime import timedelta
import json
import logging
import tempfile
from urllib.parse import urlparse

import boto3
from typing import Iterable, List
from uuid import UUID
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.core.files.base import File
from sentry_sdk import capture_exception
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from weni.feature_flags.services import FeatureFlagsService


from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.apps.archive_chats.serializers import ArchiveMessageSerializer
from chats.apps.core.integrations.aws.s3.helpers import is_file_in_the_same_bucket
from chats.apps.core.integrations.aws.s3.helpers import get_presigned_url
from chats.apps.rooms.models import Room
from chats.apps.msgs.models import Message, MessageMedia


logger = logging.getLogger(__name__)


def is_file_on_chats_bucket(url: str) -> bool:
    return is_file_in_the_same_bucket(url, settings.AWS_STORAGE_BUCKET_NAME)


class BaseArchiveChatsService(ABC):
    @abstractmethod
    def archive_room_history(self, room: Room, job: ArchiveConversationsJob) -> None:
        pass

    @abstractmethod
    def process_messages(
        self, room_archived_conversation: RoomArchivedConversation
    ) -> Iterable[dict]:
        pass

    @abstractmethod
    def upload_messages_file(
        self,
        room_archived_conversation: RoomArchivedConversation,
        messages: Iterable[dict],
    ) -> None:
        pass

    @abstractmethod
    def get_archived_media_url(self, object_key: str) -> str:
        pass

    @abstractmethod
    def delete_room_messages(self, room: Room) -> None:
        pass


class ArchiveChatsService(BaseArchiveChatsService):
    def __init__(self, bucket=None):
        bucket_name_from_settings = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)

        if not bucket_name_from_settings and not bucket:
            raise ValueError(
                "AWS_STORAGE_BUCKET_NAME is not set and no bucket was provided"
            )

        self.bucket = bucket or boto3.resource("s3").Bucket(bucket_name_from_settings)

    def start_archive_job(self) -> ArchiveConversationsJob:
        logger.info("[ArchiveChatsService] Starting archive job")

        return ArchiveConversationsJob.objects.create(
            started_at=timezone.now(),
        )

    def archive_room_history(self, room: Room, job: ArchiveConversationsJob) -> None:
        logger.info(
            f"[ArchiveChatsService] Archiving room history for room {room.uuid} with job {job.uuid}"
        )

        room_archived_conversation = self._claim_room_for_archive(room, job)

        if room_archived_conversation is None:
            return None

        if (
            room_archived_conversation.status
            == ArchiveConversationsJobStatus.FINISHED
        ):
            return room_archived_conversation

        try:
            if self._needs_processing_and_upload(room_archived_conversation):
                messages_data = self.process_messages(room_archived_conversation)
                self.upload_messages_file(room_archived_conversation, messages_data)
            else:
                logger.info(
                    f"[ArchiveChatsService] Skipping message processing and upload "
                    f"for room {room.uuid} - file already uploaded"
                )

            room_archived_conversation.refresh_from_db()

            if self._needs_message_deletion(room_archived_conversation):
                if (
                    room_archived_conversation.status
                    != ArchiveConversationsJobStatus.MESSAGES_FILE_UPLOADED
                ):
                    room_archived_conversation.status = (
                        ArchiveConversationsJobStatus.MESSAGES_FILE_UPLOADED
                    )
                    room_archived_conversation.save(update_fields=["status"])
                self.delete_room_messages(room_archived_conversation)
            else:
                logger.info(
                    f"[ArchiveChatsService] Skipping message deletion "
                    f"for room {room.uuid} - messages already deleted"
                )

            room_archived_conversation.refresh_from_db()
            room_archived_conversation.status = (
                ArchiveConversationsJobStatus.FINISHED
            )
            room_archived_conversation.archive_process_finished_at = timezone.now()
            room_archived_conversation.save(
                update_fields=["status", "archive_process_finished_at"]
            )
        except Exception as e:
            sentry_event_id = capture_exception(e)
            room_archived_conversation.register_error(e, sentry_event_id)
            log_msg = (
                f"[ArchiveChatsService] Error archiving room history "
                f"for room {room.uuid} with job {job.uuid}: {e}"
            )
            logger.error(
                log_msg,
                exc_info=True,
            )

        room_archived_conversation.refresh_from_db()

        return room_archived_conversation

    def _claim_room_for_archive(
        self, room: Room, job: ArchiveConversationsJob
    ) -> "RoomArchivedConversation | None":
        """
        Acquire a brief row-level lock to claim a room for archiving.

        The lock is only held long enough to:
          * read or create the RoomArchivedConversation row,
          * verify no other worker is actively processing it,
          * stamp ``archive_process_started_at`` and re-point ``job``.

        The heavy work (message iteration, S3 upload, batched DB deletes)
        runs OUTSIDE the lock so the transaction is open for milliseconds
        rather than for the duration of the upload. Concurrency is then
        protected by:
          * the row lock during the claim itself,
          * the unique constraint on ``room``,
          * the soft lock (``_is_actively_processed``) for the rare case
            where a duplicate task is dispatched while a previous attempt
            is still in flight.

        Returns the row when it is safe to proceed, an already-FINISHED
        row (which the caller should short-circuit on), or ``None`` when
        another worker holds or has recently claimed the row.
        """
        with transaction.atomic():
            room_archived_conversation = (
                RoomArchivedConversation.objects.select_for_update(skip_locked=True)
                .filter(room=room)
                .first()
            )

            if room_archived_conversation is None:
                if RoomArchivedConversation.objects.filter(room=room).exists():
                    logger.info(
                        f"[ArchiveChatsService] Room {room.uuid} is being processed "
                        f"by another worker, skipping"
                    )
                    return None

                try:
                    with transaction.atomic():
                        room_archived_conversation = (
                            RoomArchivedConversation.objects.create(
                                job=job,
                                room=room,
                                status=ArchiveConversationsJobStatus.PENDING,
                            )
                        )
                except IntegrityError:
                    logger.info(
                        f"[ArchiveChatsService] Room {room.uuid} was concurrently "
                        f"created by another worker, skipping"
                    )
                    return None

                logger.info(
                    f"[ArchiveChatsService] Room archived conversation created: "
                    f"{room_archived_conversation.uuid} with status "
                    f"{room_archived_conversation.status} for room {room.uuid} "
                    f"and job {job.uuid}"
                )

            if (
                room_archived_conversation.status
                == ArchiveConversationsJobStatus.FINISHED
            ):
                logger.info(
                    f"[ArchiveChatsService] Room {room.uuid} is already archived "
                    f"(conversation {room_archived_conversation.uuid}), skipping"
                )
                return room_archived_conversation

            if self._is_actively_processed(room_archived_conversation):
                logger.info(
                    f"[ArchiveChatsService] Room {room.uuid} is already being "
                    f"processed (conversation {room_archived_conversation.uuid}, "
                    f"status {room_archived_conversation.status}, "
                    f"started_at {room_archived_conversation.archive_process_started_at}), "
                    f"skipping"
                )
                return None

            update_fields = ["archive_process_started_at"]
            room_archived_conversation.archive_process_started_at = timezone.now()

            if room_archived_conversation.job_id != job.uuid:
                logger.info(
                    f"[ArchiveChatsService] Resuming room archived conversation "
                    f"{room_archived_conversation.uuid} with status "
                    f"{room_archived_conversation.status} "
                    f"for room {room.uuid} and job {job.uuid}"
                )
                room_archived_conversation.job = job
                update_fields.append("job")

            room_archived_conversation.save(update_fields=update_fields)

            return room_archived_conversation

    def _is_actively_processed(
        self, room_archived_conversation: "RoomArchivedConversation"
    ) -> bool:
        """
        Soft-lock detection used after the row lock is released.

        A row is considered actively processed when its status indicates
        an in-progress pipeline step and ``archive_process_started_at``
        is recent enough that another worker is plausibly still running.

        FINISHED and FAILED rows are never considered active, since they
        represent terminal-or-retriable states that must be allowed to
        progress (FINISHED short-circuits in the caller; FAILED is
        explicitly resumable).

        The threshold is configurable via the
        ``ARCHIVE_CHATS_IN_PROGRESS_TIMEOUT_HOURS`` setting and defaults
        to 12 hours, which is comfortably above the configured task
        expiration but short enough to recover from a crashed worker
        within a day.
        """
        if room_archived_conversation.status in {
            ArchiveConversationsJobStatus.FINISHED,
            ArchiveConversationsJobStatus.FAILED,
        }:
            return False

        started_at = room_archived_conversation.archive_process_started_at
        if started_at is None:
            return False

        threshold_hours = getattr(
            settings, "ARCHIVE_CHATS_IN_PROGRESS_TIMEOUT_HOURS", 12
        )
        return timezone.now() - started_at < timedelta(hours=threshold_hours)

    def _get_or_create_room_archived_conversation(
        self, room: Room, job: ArchiveConversationsJob
    ) -> RoomArchivedConversation:
        existing = RoomArchivedConversation.objects.filter(room=room).first()

        if existing:
            if existing.status != ArchiveConversationsJobStatus.FINISHED:
                logger.info(
                    f"[ArchiveChatsService] Resuming room archived conversation "
                    f"{existing.uuid} with status {existing.status} "
                    f"for room {room.uuid} and job {job.uuid}"
                )
                existing.job = job
                existing.save(update_fields=["job"])
            return existing

        room_archived_conversation = RoomArchivedConversation.objects.create(
            job=job,
            room=room,
            status=ArchiveConversationsJobStatus.PENDING,
        )
        logger.info(
            f"[ArchiveChatsService] Room archived conversation created: "
            f"{room_archived_conversation.uuid} with status "
            f"{room_archived_conversation.status} for room {room.uuid} "
            f"and job {job.uuid}"
        )
        return room_archived_conversation

    def _needs_processing_and_upload(
        self, room_archived_conversation: RoomArchivedConversation
    ) -> bool:
        status = room_archived_conversation.status
        if status in {
            ArchiveConversationsJobStatus.MESSAGES_FILE_UPLOADED,
            ArchiveConversationsJobStatus.DELETING_MESSAGES_FROM_DB,
            ArchiveConversationsJobStatus.MESSAGES_DELETED_FROM_DB,
        }:
            return False
        if (
            status == ArchiveConversationsJobStatus.FAILED
            and room_archived_conversation.file
        ):
            return False
        return True

    def _needs_message_deletion(
        self, room_archived_conversation: RoomArchivedConversation
    ) -> bool:
        status = room_archived_conversation.status
        if status == ArchiveConversationsJobStatus.MESSAGES_DELETED_FROM_DB:
            return False
        if (
            status == ArchiveConversationsJobStatus.FAILED
            and room_archived_conversation.messages_deleted_at
        ):
            return False
        return True

    def process_messages(
        self, room_archived_conversation: RoomArchivedConversation
    ) -> Iterable[dict]:
        room = room_archived_conversation.room

        room_archived_conversation.status = (
            ArchiveConversationsJobStatus.PROCESSING_MESSAGES
        )
        room_archived_conversation.archive_process_started_at = timezone.now()
        room_archived_conversation.save(
            update_fields=["status", "archive_process_started_at"]
        )

        logger.info(
            f"[ArchiveChatsService] Room archived conversation status updated to "
            f"{room_archived_conversation.status} for room {room.uuid} "
            f"with archived conversation {room_archived_conversation.uuid}"
        )

        return self._iter_messages(room)

    def _iter_messages(self, room: Room) -> Iterable[dict]:
        page_size = settings.ARCHIVE_CHATS_MESSAGE_PAGE_SIZE
        last_created_on = None
        last_pk = None

        while True:
            qs = (
                Message.objects.filter(room=room)
                .select_related(
                    "user", "contact", "automatic_message", "internal_note"
                )
                .prefetch_related("medias", "internal_note__medias")
                .order_by("created_on", "pk")
            )
            if last_pk is not None:
                qs = qs.filter(
                    Q(created_on__gt=last_created_on)
                    | Q(created_on=last_created_on, pk__gt=last_pk)
                )

            page = list(qs[:page_size])
            if not page:
                break

            for message in page:
                message_context = {"media": []}
                for media in message.medias.all():
                    url = self.process_media(media)
                    if url:
                        message_context["media"].append(
                            {
                                "url": url,
                                "content_type": media.content_type,
                                "created_on": media.created_on.isoformat(),
                            }
                        )

                yield ArchiveMessageSerializer(message, context=message_context).data

            last_created_on = page[-1].created_on
            last_pk = page[-1].pk

    def upload_messages_file(
        self,
        room_archived_conversation: RoomArchivedConversation,
        messages: Iterable[dict],
    ) -> None:

        if (
            room_archived_conversation.status
            != ArchiveConversationsJobStatus.PROCESSING_MESSAGES
        ):
            raise ValidationError(
                f"Room archived conversation {room_archived_conversation.uuid} is not in processing messages status"
            )

        with tempfile.SpooledTemporaryFile(max_size=5 * 1024 * 1024) as tmp:
            for message in messages:
                tmp.write(json.dumps(message, ensure_ascii=False).encode("utf-8"))
                tmp.write(b"\n")

            room_archived_conversation.status = (
                ArchiveConversationsJobStatus.UPLOADING_MESSAGES_FILE
            )
            room_archived_conversation.save(update_fields=["status"])

            logger.info(
                f"[ArchiveChatsService] Room archived conversation status updated to "
                f"{room_archived_conversation.status} for room {room_archived_conversation.room.uuid} "
                f"with archived conversation {room_archived_conversation.uuid}"
            )

            tmp.seek(0)

            room_archived_conversation.file.save(
                "messages.jsonl",
                File(tmp),
                save=True,
            )

        room_archived_conversation.status = (
            ArchiveConversationsJobStatus.MESSAGES_FILE_UPLOADED
        )
        room_archived_conversation.save(update_fields=["status"])

        return room_archived_conversation

    def process_media(self, media: MessageMedia) -> None:
        if not media.media_file:
            if not media.media_url:
                return

            if is_file_on_chats_bucket(media.media_url):
                return self._get_chats_media_redirect_url(media.media_url)

            object_key = urlparse(media.media_url).path.lstrip("/")
            return self._get_flows_media_redirect_url(object_key)

        if is_file_on_chats_bucket(media.media_file.url):
            object_key = media.media_file.name

            return self._get_chats_media_redirect_url(object_key)

        return None

    def _get_chats_media_redirect_url(self, object_key: str) -> str:
        base_url = settings.CHATS_BASE_URL
        path = reverse("get_archived_media")

        return f"{base_url}{path}?object_key={object_key}"

    def _get_flows_media_redirect_url(self, object_key: str) -> str:
        base_url = settings.FLOWS_BASE_URL
        path = f"{base_url}/api/v2/internals/media/download"

        return f"{path}/{object_key}"

    def get_archived_media_url(self, object_key: str) -> str:
        return get_presigned_url(object_key)

    def delete_room_messages(
        self,
        room_archived_conversation: RoomArchivedConversation,
        batch_size: int = 1000,
    ) -> None:
        room_archived_conversation.refresh_from_db()

        if (
            room_archived_conversation.status
            != ArchiveConversationsJobStatus.MESSAGES_FILE_UPLOADED
        ):
            raise ValidationError(
                f"Room archived conversation {room_archived_conversation.uuid} is not in messages file uploaded status"
            )

        room = room_archived_conversation.room

        logger.info(
            f"[ArchiveChatsService] Deleting room messages for room {room.uuid}"
        )

        deleted = 0
        while True:
            with transaction.atomic():
                messages_pks = list(
                    Message.objects.filter(room=room).values_list("pk", flat=True)[
                        :batch_size
                    ]
                )
                if not messages_pks:
                    break

                Message.objects.filter(pk__in=messages_pks).delete()
                deleted += len(messages_pks)

        logger.info(
            f"[ArchiveChatsService] Deleted {deleted} messages for room {room.uuid}"
        )

        room_archived_conversation.status = (
            ArchiveConversationsJobStatus.MESSAGES_DELETED_FROM_DB
        )
        room_archived_conversation.messages_deleted_at = timezone.now()
        room_archived_conversation.save(
            update_fields=["status", "messages_deleted_at"]
        )

        logger.info(
            f"[ArchiveChatsService] Room archived conversation status updated to "
            f"{room_archived_conversation.status} for room {room.uuid} "
            f"with archived conversation {room_archived_conversation.uuid}"
        )

        return room_archived_conversation

    def get_projects(self) -> List[UUID]:
        feature_flags_service = FeatureFlagsService()
        feature_flag_key = settings.ARCHIVE_CHATS_PROJECTS_LIST_FEATURE_FLAG_KEY
        features = feature_flags_service.get_features()

        projects_list_feature_flag = features.get(feature_flag_key)

        if not projects_list_feature_flag:
            return []

        try:
            projects_list = projects_list_feature_flag["rules"][0]["condition"][
                "projectUUID"
            ]["$in"]
        except Exception as e:
            event_id = capture_exception(e)

            logger.error(
                "[ArchiveChatsService] Error getting projects list from feature flag "
                f"{feature_flag_key}: {e} with event id {event_id}",
                exc_info=True,
            )

            return []

        return projects_list
