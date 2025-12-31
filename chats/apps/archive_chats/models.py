import traceback
import uuid

from typing import Optional
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.uploads import upload_to
from chats.apps.rooms.models import Room


class ArchiveConversationsJob(models.Model):
    uuid = models.UUIDField(
        _("UUID"),
        default=uuid.uuid4,
        help_text=_("The UUID of the job"),
        unique=True,
        editable=False,
        primary_key=True,
    )
    started_at = models.DateTimeField(
        _("Started at"),
        null=True,
        blank=True,
        help_text=_("The date and time when the job started"),
    )

    class Meta:
        verbose_name = _("Archive Conversations Job")
        verbose_name_plural = _("Archive Conversations Jobs")

    def __str__(self):
        return f"Archive Conversations Job {self.uuid} - {self.started_at}"


class RoomArchivedConversation(models.Model):
    uuid = models.UUIDField(
        _("UUID"),
        default=uuid.uuid4,
        help_text=_("The UUID of the room archived conversation"),
        unique=True,
        editable=False,
        primary_key=True,
    )
    status = models.CharField(
        verbose_name=_("Status"),
        max_length=25,
        choices=ArchiveConversationsJobStatus.choices,
        default=ArchiveConversationsJobStatus.PENDING,
    )
    job = models.ForeignKey(
        ArchiveConversationsJob,
        verbose_name=_("Job"),
        on_delete=models.CASCADE,
        related_name="room_archived_conversations",
        help_text=_("The job that archived the conversation"),
    )
    room = models.ForeignKey(
        Room,
        verbose_name=_("Room"),
        on_delete=models.CASCADE,
        related_name="archived_conversations",
        help_text=_("The room that was archived"),
    )
    file = models.FileField(
        verbose_name=_("File"),
        upload_to=upload_to,
        help_text=_("The file that contains the archived conversation"),
        max_length=255,
    )
    archive_process_started_at = models.DateTimeField(
        verbose_name=_("Archive process started at"),
        null=True,
        blank=True,
        help_text=_("The date and time when the archive process started"),
    )
    archive_process_finished_at = models.DateTimeField(
        verbose_name=_("Archive process finished at"),
        null=True,
        blank=True,
        help_text=_("The date and time when the conversation was archived"),
    )
    messages_deleted_at = models.DateTimeField(
        verbose_name=_("Messages deleted at"),
        null=True,
        blank=True,
        help_text=_(
            "The date and time when the messages were deleted from the database"
        ),
    )
    archive_process_finished_at = models.DateTimeField(
        verbose_name=_("Archive process finished at"),
        null=True,
        blank=True,
        help_text=_("The date and time when the archive process was finished"),
    )
    failed_at = models.DateTimeField(
        verbose_name=_("Failed at"),
        null=True,
        blank=True,
        help_text=_("The date and time when the archive process failed"),
    )
    errors = models.JSONField(
        verbose_name=_("Errors"),
        null=True,
        blank=True,
        help_text=_("The errors that occurred during the archive process"),
    )

    class Meta:
        verbose_name = _("Room Archived Conversation")
        verbose_name_plural = _("Room Archived Conversations")

    def __str__(self):
        return f"Room Archived Conversation {self.room.uuid} - {self.room.queue.sector.project.name}"

    def register_error(self, error: Exception, sentry_event_id: Optional[str] = None):
        errors = self.errors or []
        errors.append(
            {
                "timestamp": str(timezone.now()),
                "error": str(error),
                "traceback": traceback.format_exception(
                    type(error), error, error.__traceback__
                ),
                "sentry_event_id": sentry_event_id,
            }
        )
        self.errors = errors
        self.save(update_fields=["errors"])
