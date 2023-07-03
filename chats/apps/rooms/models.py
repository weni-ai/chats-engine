import json
from datetime import timedelta

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from chats.core.models import BaseModel
from chats.utils.websockets import send_channels_group


class Room(BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_is_active = self.is_active

    user = models.ForeignKey(
        "accounts.User",
        related_name="rooms",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        to_field="email",
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        related_name="rooms",
        verbose_name=_("contact"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    queue = models.ForeignKey(
        "queues.Queue",
        related_name="rooms",
        verbose_name=_("Queue"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    custom_fields = models.JSONField(
        _("custom fields"),
        blank=True,
        null=True,
    )
    urn = models.CharField(_("urn"), null=True, blank=True, max_length=100, default="")

    callback_url = models.TextField(_("Callback URL"), null=True, blank=True)

    ended_at = models.DateTimeField(
        _("Ended at"), auto_now_add=False, null=True, blank=True
    )

    ended_by = models.CharField(_("Ended by"), max_length=50, null=True, blank=True)

    is_active = models.BooleanField(_("is active?"), default=True)
    is_waiting = models.BooleanField(_("is waiting for answer?"), default=False)

    transfer_history = models.JSONField(_("Transfer History"), null=True, blank=True)

    tags = models.ManyToManyField(
        "sectors.SectorTag",
        related_name="rooms",
        verbose_name=_("tags"),
        blank=True,
    )

    class Meta:
        verbose_name = _("Room")
        verbose_name_plural = _("Rooms")
        constraints = [
            models.UniqueConstraint(
                fields=["contact", "queue"],
                condition=models.Q(is_active=True),
                name="unique_contact_queue_is_activetrue_room",
            )
        ]

    def save(self, *args, **kwargs) -> None:
        if self.__original_is_active is False:
            raise ValidationError({"detail": _("Closed rooms cannot receive updates")})
        return super().save(*args, **kwargs)

    def get_permission(self, user):
        try:
            return self.queue.get_permission(user)
        except ObjectDoesNotExist:
            return None

    def get_is_waiting(self):
        """If the room does not have any contact message, then it is waiting"""
        check_messages = (
            self.is_waiting
            if self.is_waiting
            else not self.messages.filter(contact__isnull=False).exists()
        )
        check_flowstarts = self.flowstarts.filter(is_deleted=False).exists()
        return check_messages or check_flowstarts

    @property
    def last_contact_message(self):
        return (
            self.messages.filter(contact__isnull=False).order_by("-created_on").first()
        )

    def trigger_default_message(self):
        default_message = self.queue.default_message
        if default_message is not None:
            sent_message = self.messages.create(
                user=None, contact=None, text=default_message
            )
            sent_message.notify_room("create", True)

    @property
    def is_24h_valid(self) -> bool:
        """Validates is the last contact message was sent more than a day ago"""
        if not self.urn.startswith("whatsapp"):
            return True

        day_validation = self.messages.filter(
            created_on__gte=timezone.now() - timedelta(days=1),
            contact=self.contact,
        )
        return day_validation.exists()

    @property
    def serialized_ws_data(self):
        from chats.apps.api.v1.rooms.serializers import RoomSerializer  # noqa

        return RoomSerializer(self).data

    def close(self, tags: list = [], end_by: str = ""):
        self.is_active = False
        self.ended_at = timezone.now()
        self.ended_by = end_by
        if tags is not None:
            self.tags.add(*tags)
        self.save()

    def request_callback(self, room_data: dict):
        if self.callback_url is None:
            return None

        requests.post(
            self.callback_url,
            data=json.dumps(
                {"type": "room.update", "content": room_data},
                sort_keys=True,
                indent=1,
                cls=DjangoJSONEncoder,
            ),
            headers={"content-type": "application/json"},
        )

    def base_notification(self, content, action):
        if self.user:
            permission = self.get_permission(self.user)
            group_name = f"permission_{permission.pk}"
        else:
            group_name = f"queue_{self.queue.pk}"

        send_channels_group(
            group_name=group_name,
            call_type="notify",
            content=content,
            action=action,
        )

    def notify_queue(
        self, action: str, callback: bool = False, transferred_by: str = ""
    ):
        """
        Used to notify channels groups when something happens on the instance.

        Actions:
        Create

        e.g.:
        Contact create new room,
        Call the sector group(all agents) and send the 'create' action to add them in the room group
        """
        content = self.serialized_ws_data
        if transferred_by != "":
            content["transferred_by"] = transferred_by
        send_channels_group(
            group_name=f"queue_{self.queue.pk}",
            call_type="notify",
            content=content,
            action=f"rooms.{action}",
        )
        if self.callback_url and callback and action in ["update", "destroy", "close"]:
            self.request_callback(self.serialized_ws_data)

    def notify_room(self, action: str, callback: bool = False):
        """
        Used to notify channels groups when something happens on the instance.

        Actions:
        Update, Delete

        e.g.:
        Agent enters room,
        Call the sector group(all agents) and send the 'update' action to remove them from the group
        """
        if self.user:
            self.notify_user(action=action)
        else:
            self.notify_queue(action=action)

        if self.callback_url and callback and action in ["update", "destroy", "close"]:
            self.request_callback(self.serialized_ws_data)

    def notify_user(self, action: str, user=None, transferred_by: str = ""):
        user = user if user else self.user
        permission = self.get_permission(user)
        content = self.serialized_ws_data
        if transferred_by != "":
            content["transferred_by"] = transferred_by

        send_channels_group(
            group_name=f"permission_{permission.pk}",
            call_type="notify",
            content=content,
            action=f"rooms.{action}",
        )

    def user_connection(self, action: str, user=None):
        user = user if user else self.user
        permission = self.get_permission(user)
        send_channels_group(
            group_name=f"permission_{permission.pk}",
            call_type=action,
            content={"name": "room", "id": str(self.pk)},
            action=f"groups.{action}",
        )

    def queue_connection(self, action: str, queue=None):
        queue = queue if queue else self.queue

        send_channels_group(
            group_name=f"queue_{queue.pk}",
            call_type=action,
            content={"name": "room", "id": str(self.pk)},
            action=f"group.{action}",
        )
