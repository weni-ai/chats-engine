import json
import logging

import sentry_sdk
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from chats.core.models import BaseModelWithManualCreatedOn, BaseModel
from chats.core.requests import get_request_session_with_retries

logger = logging.getLogger(__name__)


def message_media_upload_to(instance, filename):
    """
    Generate unique file path for MessageMedia uploads using UUID.
    This prevents file name collisions when multiple messages are sent
    in the same second with the same original filename.
    
    Args:
        instance: MessageMedia instance
        filename: Original filename from upload
        
    Returns:
        str: Unique file path in format: messagemedia/{uuid}{extension}
    """
    from pathlib import Path
    ext = Path(filename).suffix.lower()
    return f"messagemedia/{instance.uuid}{ext}"


class Message(BaseModelWithManualCreatedOn):
    room = models.ForeignKey(
        "rooms.Room",
        related_name="messages",
        verbose_name=_("room"),
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "accounts.User",
        related_name="messages",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        to_field="email",
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        related_name="messages",
        verbose_name=_("contact"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    text = models.TextField(_("Text"), blank=True, null=True)
    seen = models.BooleanField(_("Was it seen?"), default=False)
    external_id = models.CharField(
        _("External ID"), max_length=200, blank=True, null=True
    )
    metadata = models.JSONField(
        _("message metadata"), blank=True, null=True, default=dict
    )
    status = models.JSONField(
        _("message status"),
        blank=True,
        null=True,
    )
    is_read = models.CharField(
        _("message is read"), max_length=50, blank=True, null=True
    )
    is_delivered = models.CharField(
        _("message is delivered"), max_length=50, blank=True, null=True
    )

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["created_on"]

    def save(self, *args, **kwargs) -> None:
        if self.room.is_active is False:
            raise ValidationError({"detail": _("Closed rooms cannot receive messages")})
        if self.room.is_24h_valid is False and self.user is not None:
            raise ValidationError(
                {
                    "detail": _(
                        "You cannot send messages after 24h from the last contact message"
                    )
                }
            )

        return super().save(*args, **kwargs)

    @property
    def serialized_ws_data(self) -> dict:
        from chats.apps.api.v1.msgs.serializers import MessageWSSerializer

        return dict(MessageWSSerializer(self).data)

    @property
    def signed_text(self):
        return f"{self.user.first_name}:\n\n{self.text}"

    def get_authorization(self, user):
        return self.room.get_authorization(user)

    def media(self):
        return self.medias.all()

    def get_sender(self):
        return self.user or self.contact

    def update_msg_text_with_signature(self, msg_data: dict):
        if self.user and self.room.queue.sector.sign_messages and self.text:
            msg_data["text"] = self.signed_text
        return msg_data

    def notify_room(self, action: str, callback: bool = False):
        """Notify room about message changes with optional webhook callback"""
        data = self.serialized_ws_data
        self.room.base_notification(content=data, action=f"msg.{action}")

        if self.room.callback_url and callback:
            data = self.update_msg_text_with_signature(data)

            request_session = get_request_session_with_retries(
                retries=getattr(settings, "CALLBACK_RETRY_COUNT", 5),
                backoff_factor=getattr(settings, "CALLBACK_RETRY_BACKOFF_FACTOR", 0.1),
                status_forcelist=getattr(
                    settings,
                    "CALLBACK_RETRYABLE_STATUS_CODES",
                    [429, 500, 502, 503, 504, 404],
                ),
                method_whitelist=["POST"],
            )

            try:
                timeout = getattr(settings, "CALLBACK_TIMEOUT_SECONDS", None)

                response = request_session.post(
                    self.room.callback_url,
                    data=json.dumps(
                        {"type": "msg.create", "content": data},
                        sort_keys=True,
                        indent=1,
                        cls=DjangoJSONEncoder,
                    ),
                    headers={"content-type": "application/json"},
                    timeout=timeout,
                )

                if response.status_code >= 400:
                    error_msg = (
                        f"[Message.notify_room] Callback failed - "
                        f"Message ID: {self.pk}, "
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )
                    logger.error(error_msg)

                    sentry_sdk.capture_message(
                        error_msg,
                        level="error",
                        extras={
                            "message_uuid": self.pk,
                            "room_uuid": self.room.uuid,
                            "callback_url": self.room.callback_url,
                            "status_code": response.status_code,
                            "response_text": response.text[:500],
                        },
                    )

            except Exception as error:
                error_msg = (
                    f"[Message.notify_room] Callback failed - "
                    f"Message ID: {self.pk}, "
                    f"Error: {type(error).__name__}: {str(error)[:200]}"
                )
                logger.error(error_msg)

                sentry_sdk.capture_exception(
                    error,
                    extras={
                        "message_uuid": self.pk,
                        "room_uuid": self.room.uuid,
                        "callback_url": self.room.callback_url,
                    },
                )

    @property
    def project(self):
        return self.room.project

    @property
    def is_automatic_message(self):
        return hasattr(self, "automatic_message") and self.automatic_message is not None


class MessageMedia(BaseModelWithManualCreatedOn):
    message = models.ForeignKey(
        Message,
        related_name="medias",
        verbose_name=_("message"),
        on_delete=models.CASCADE,
    )
    content_type = models.CharField(_("Content Type"), max_length=300)
    media_file = models.FileField(
        _("Media File"),
        null=True,
        blank=True,
        max_length=300,
        upload_to=message_media_upload_to,
    )
    media_url = models.TextField(_("Media url"), null=True, blank=True)

    class Meta:
        verbose_name = _("MessageMedia")
        verbose_name_plural = _("MessageMedias")
        indexes = [
            models.Index(
                fields=["content_type"],
                name="message_media_content_type_idx",
            ),
        ]

    def __str__(self):
        return f"{self.message.pk} - {self.url}"

    def save(self, *args, **kwargs) -> None:
        if self.message.room.is_active is False:
            raise ValidationError({"detail": _("Closed rooms cannot receive messages")})
        return super().save(*args, **kwargs)

    @property
    def url(self):
        url = self.media_file.url if self.media_file else self.media_url
        try:
            if url.startswith("/"):
                url = settings.ENGINE_BASE_URL + url
        except AttributeError:
            return ""
        return url

    def get_authorization(self, user):
        return self.room.get_authorization(user)

    def callback(self):
        """Send webhook callback for MessageMedia"""
        msg_data = self.message.serialized_ws_data
        msg_data["text"] = ""

        if self.message.room.callback_url:
            request_session = get_request_session_with_retries(
                retries=getattr(settings, "CALLBACK_RETRY_COUNT", 5),
                backoff_factor=getattr(settings, "CALLBACK_RETRY_BACKOFF_FACTOR", 0.1),
                status_forcelist=getattr(
                    settings,
                    "CALLBACK_RETRYABLE_STATUS_CODES",
                    [429, 500, 502, 503, 504],
                ),
                method_whitelist=["POST"],
            )

            try:
                timeout = getattr(settings, "CALLBACK_TIMEOUT_SECONDS", None)

                response = request_session.post(
                    self.message.room.callback_url,
                    data=json.dumps(
                        {"type": "msg.create", "content": msg_data},
                        sort_keys=True,
                        indent=1,
                        cls=DjangoJSONEncoder,
                    ),
                    headers={"content-type": "application/json"},
                    timeout=timeout,
                )

                if response.status_code >= 400:
                    error_msg = (
                        f"[MessageMedia.callback] Callback failed - "
                        f"MessageMedia ID: {self.pk}, "
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )
                    logger.error(error_msg)

                    sentry_sdk.capture_message(
                        error_msg,
                        level="error",
                        extras={
                            "media_uuid": self.pk,
                            "message_uuid": self.message.pk,
                            "room_uuid": self.message.room.uuid,
                            "callback_url": self.message.room.callback_url,
                            "status_code": response.status_code,
                            "response_text": response.text[:500],
                        },
                    )

            except Exception as error:
                error_msg = (
                    f"[MessageMedia.callback] Callback failed - "
                    f"MessageMedia ID: {self.pk}, "
                    f"Error: {type(error).__name__}: {str(error)[:200]}"
                )
                logger.error(error_msg)

                sentry_sdk.capture_exception(
                    error,
                    extras={
                        "media_uuid": self.pk,
                        "message_uuid": self.message.pk,
                        "room_uuid": self.message.room.uuid,
                        "callback_url": self.message.room.callback_url,
                    },
                )

    def notify_room(self, action: str = "create", callback: bool = False):
        """Delegate room notification to the associated Message"""
        self.message.notify_room(action, callback)

    @property
    def project(self):
        return self.message.project


class ChatMessageReplyIndex(BaseModelWithManualCreatedOn):
    external_id = models.CharField(
        _("External ID"), max_length=255, unique=True, db_index=True
    )
    message = models.ForeignKey(
        "Message", on_delete=models.CASCADE, related_name="reply_indexes"
    )

    class Meta:
        verbose_name = "Chat Message Reply Index"
        verbose_name_plural = "Chat Message Reply Indexes"


class AutomaticMessage(BaseModel):
    """
    Automatic message for a room.

    This is only used as a reference for a message that is sent automatically
    when the room is first assigned to a user.

    A room can only have one automatic message.
    """

    message = models.OneToOneField(
        "msgs.Message", on_delete=models.CASCADE, related_name="automatic_message"
    )
    room = models.OneToOneField(
        "rooms.Room", on_delete=models.CASCADE, related_name="automatic_message"
    )

    class Meta:
        verbose_name = "Automatic Message"
        verbose_name_plural = "Automatic Messages"

    def __str__(self):
        return f"{self.room.uuid} - {self.message.uuid}"
