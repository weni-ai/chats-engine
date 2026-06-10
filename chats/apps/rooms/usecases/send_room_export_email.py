"""Uploads room export files to S3 and notifies the requester by email.

This is the delivery step of the room export pipeline. It receives the bytes
produced by `RenderRoomExport`, stores each format in S3 under the room's
namespace and sends one email per file, reusing the existing report email
templates so users have a consistent experience across export flows.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Dict

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives

from chats.apps.rooms.email_templates import (
    get_room_export_failed_email,
    get_room_export_ready_email,
)
from chats.core.storages import RoomExportStorage

if TYPE_CHECKING:
    from chats.apps.rooms.models import Room


logger = logging.getLogger(__name__)


DEFAULT_DOWNLOAD_URL_EXPIRATION = int(timedelta(days=7).total_seconds())


class SendRoomExportEmail:
    """Uploads export files to S3 and sends one download email per file."""

    def __init__(
        self,
        storage: RoomExportStorage = None,
        download_url_expiration: int = DEFAULT_DOWNLOAD_URL_EXPIRATION,
    ):
        self.storage = storage or RoomExportStorage()
        self.download_url_expiration = download_url_expiration

    def execute(
        self, room: "Room", files: Dict[str, bytes], recipient_email: str
    ) -> Dict[str, str]:
        """Uploads files and sends one email per generated format.

        Args:
            room: Room being exported (used for naming and identifier).
            files: Mapping of extension (html/pdf) to the file bytes.
            recipient_email: Address to receive the download links.

        Returns:
            Mapping of extension to the pre-signed download URL that was sent.
        """
        if not files:
            raise ValueError("No files to upload")

        # Two-phase delivery: upload everything first, then send emails. This
        # prevents partial delivery (one email sent, another upload failing)
        # which would cause duplicate emails when the task is retried.
        download_urls: Dict[str, str] = {}
        for extension, content in files.items():
            download_urls[extension] = self._upload_single_file(
                room, extension, content
            )

        for extension, download_url in download_urls.items():
            self._send_ready_email(room, download_url, recipient_email)

        return download_urls

    def send_failure_notification(
        self, room: "Room", recipient_email: str, error_message: str = None
    ) -> None:
        """Sends the failure notification email to the requester."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        identifier = self._room_identifier(room)
        subject = (
            f"Error generating conversation export for room "
            f"{identifier} - {timestamp}"
        )
        message_plain, message_html = get_room_export_failed_email(
            identifier, error_message
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body=message_plain,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        email.attach_alternative(message_html, "text/html")
        email.send(fail_silently=False)

        logger.info(
            "Room export failure email sent to %s | room=%s",
            recipient_email,
            room.uuid,
        )

    def _upload_single_file(self, room: "Room", extension: str, content: bytes) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        filename = self._build_filename(room, extension, timestamp)
        path = self.storage.save(filename, ContentFile(content))
        download_url = self.storage.get_download_url(
            path, expiration=self.download_url_expiration
        )

        logger.info(
            "Room export file uploaded | room=%s | path=%s",
            room.uuid,
            path,
        )
        return download_url

    def _send_ready_email(
        self, room: "Room", download_url: str, recipient_email: str
    ) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        identifier = self._room_identifier(room)
        subject = f"Conversation export for room {identifier} - {timestamp}"
        message_plain, message_html = get_room_export_ready_email(
            identifier, download_url
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body=message_plain,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        email.attach_alternative(message_html, "text/html")
        email.extra_headers = {
            "X-No-Track": "True",
            "X-Track-Click": "no",
            "o:tracking-clicks": "no",
        }
        email.send(fail_silently=False)

        logger.info(
            "Room export ready email sent to %s | room=%s",
            recipient_email,
            room.uuid,
        )

    def _build_filename(self, room: "Room", extension: str, timestamp: str) -> str:
        return f"{room.uuid}/conversation_{room.uuid}_{timestamp}.{extension}"

    def _room_identifier(self, room: "Room") -> str:
        return room.protocol or str(room.uuid)


__all__ = ["SendRoomExportEmail"]
