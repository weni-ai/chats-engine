import json

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from chats.core.models import BaseModel
from chats.utils.websockets import send_channels_group


class Room(BaseModel):
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

    callback_url = models.URLField(
        _("Callback URL"), null=True, blank=True, max_length=200
    )

    ended_at = models.DateTimeField(
        _("Ended at"), auto_now_add=False, null=True, blank=True
    )

    ended_by = models.CharField(_("Ended by"), max_length=50, null=True, blank=True)

    is_active = models.BooleanField(_("is active?"), default=True)

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

    def save(self, *args, **kwargs) -> None:
        if self.is_active is False:
            raise ValidationError(_("Closed rooms cannot receive updates"))
        return super().save(*args, **kwargs)

    def get_permission(self, user):
        return self.queue.get_permission(user)

    @property
    def serialized_ws_data(self):
        from chats.apps.api.v1.rooms.serializers import RoomSerializer  # noqa

        return RoomSerializer(self).data

    def transfer_room(self, type: str, data: dict):
        transfer_history = self.transfer_history
        transfer_history = (
            [] if transfer_history is None else json.loads(transfer_history)
        )
        user = data.get("user")
        queue = data.get("queue")
        if user:
            _content = {"type": "user", "id": user, "transfered_at": timezone.now()}
            transfer_history.append(_content)
        if queue:
            _content = {"type": "queue", "id": queue, "transfered_at": timezone.now()}
            transfer_history.append(_content)
        self.transfer_history = json.dumps(transfer_history)
        self.save()
        msg = self.messages.create(text=self.transfer_history)
        msg.notify_room("create")
        self.notify_room("update")

    def close(self, tags: list = [], end_by: str = ""):
        self.is_active = False
        self.ended_at = timezone.now()
        self.ended_by = end_by
        self.tags.add(*tags)
        self.save()

    def notify_queue(self, action):
        """
        Used to notify channels groups when something happens on the instance.

        Actions:
        Create

        e.g.:
        Contact create new room,
        Call the sector group(all agents) and send the 'create' action to add them in the room group
        """

        send_channels_group(
            group_name=f"queue_{self.queue.pk}",
            type="notify",
            content=self.serialized_ws_data,
            action=f"rooms.{action}",
        )

    def notify_room(self, action):
        """
        Used to notify channels groups when something happens on the instance.

        Actions:
        Update, Delete

        e.g.:
        Agent enters room,
        Call the sector group(all agents) and send the 'update' action to remove them from the group
        """

        send_channels_group(
            group_name=f"room_{self.pk}",
            type="notify",
            content=self.serialized_ws_data,
            action=f"rooms.{action}",
        )
