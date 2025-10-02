import json
import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING

import requests
import sentry_sdk
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_redis import get_redis_connection
from model_utils import FieldTracker
from requests.exceptions import RequestException
from rest_framework.exceptions import ValidationError

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.projects.models.models import RoomRoutingType
from chats.apps.projects.usecases.send_room_info import RoomInfoUseCase
from chats.apps.projects.usecases.status_service import InServiceStatusService
from chats.apps.rooms.exceptions import (
    MaxPinRoomLimitReachedError,
    RoomIsNotActiveError,
)
from chats.core.models import BaseConfigurableModel, BaseModel
from chats.utils.websockets import send_channels_group

if TYPE_CHECKING:
    from chats.apps.projects.models.models import Project
    from chats.apps.queues.models import Queue


logger = logging.getLogger(__name__)


class Room(BaseModel, BaseConfigurableModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_is_active = self.is_active
        self._original_user = self.user

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
    urn = models.TextField(_("urn"), null=True, blank=True, default="")

    project_uuid = models.TextField(
        _("project_uuid"), null=True, blank=True, default=""
    )
    ticket_uuid = models.UUIDField(_("ticket uuid"), null=True, blank=True)

    callback_url = models.TextField(_("Callback URL"), null=True, blank=True)

    ended_at = models.DateTimeField(
        _("Ended at"), auto_now_add=False, null=True, blank=True
    )

    ended_by = models.CharField(_("Ended by"), max_length=50, null=True, blank=True)

    is_active = models.BooleanField(_("is active?"), default=True)
    is_waiting = models.BooleanField(_("is waiting for answer?"), default=False)

    # Legacy, only stores the last transfer
    transfer_history = models.JSONField(_("Transfer History"), null=True, blank=True)
    # New, stores the full transfer history
    full_transfer_history = models.JSONField(
        _("Full Transfer History"), null=True, blank=True, default=list
    )

    tags = models.ManyToManyField(
        "sectors.SectorTag",
        related_name="rooms",
        verbose_name=_("tags"),
        blank=True,
    )
    protocol = models.TextField(_("protocol"), null=True, blank=True, default="")

    service_chat = models.TextField(
        _("service chat"), null=True, blank=True, default=""
    )

    first_user_assigned_at = models.DateTimeField(
        _("First user assigned at"), null=True, blank=True
    )
    user_assigned_at = models.DateTimeField(
        _("User assigned at"), null=True, blank=True
    )
    added_to_queue_at = models.DateTimeField(
        _("Added to queue at"), null=True, blank=True
    )

    tracker = FieldTracker(fields=["user"])

    @property
    def is_billing_notified(self) -> bool:
        """
        Returns True if the room has been billed
        """
        return self.get_config("is_billing_notified", False)

    def mark_notes_as_non_deletable(self):
        """
        Mark all notes in this room as non-deletable when room is transferred
        """
        self.notes.update(is_deletable=False)

    def notify_billing(self):
        """
        Notify the billing system and set the is_billing_notified flag to True
        """
        logger.info("Notifying billing for room %s...", self.pk)
        room_client = RoomInfoUseCase()
        room_client.get_room(self)

        self.set_config("is_billing_notified", True)
        logger.info(
            "Billing notified for room %s. Setting is_billing_notified to True",
            self.pk,
        )

    def _update_agent_service_status(self, is_new):
        """
        Atualiza o status 'In-Service' dos agentes baseado nas mudanças na sala
        Args:
            is_new: Boolean indicando se é uma sala nova
        """
        old_user = self._original_user
        new_user = self.user

        project = None
        if self.queue and hasattr(self.queue, "sector"):
            sector = self.queue.sector
            if sector and hasattr(sector, "project"):
                project = sector.project

        if not project:
            return

        if is_new and new_user:
            InServiceStatusService.room_assigned(new_user, project)
            return

        if old_user is None and new_user is not None:
            InServiceStatusService.room_assigned(new_user, project)
            return

        if old_user is not None and new_user is not None and old_user != new_user:
            InServiceStatusService.room_closed(old_user, project)
            InServiceStatusService.room_assigned(new_user, project)
            return

        if old_user is not None and new_user is None:
            InServiceStatusService.room_closed(old_user, project)
            return

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
        indexes = [
            models.Index(fields=["project_uuid"]),
        ]

    def save(self, *args, **kwargs) -> None:
        if self.__original_is_active is False:
            raise ValidationError({"detail": _("Closed rooms cannot receive updates")})

        if self._state.adding:
            self.added_to_queue_at = timezone.now()

        user_has_changed = self.pk and self.tracker.has_changed("user")

        if self.user and not self.user_assigned_at or user_has_changed:
            self.user_assigned_at = timezone.now()

        if self.is_active and self.user and not self.first_user_assigned_at:
            if self.user_assigned_at:
                self.first_user_assigned_at = self.user_assigned_at
            else:
                self.first_user_assigned_at = timezone.now()

        if user_has_changed and not self.user:
            self.added_to_queue_at = timezone.now()

        if user_has_changed:
            self.clear_pins()

        is_new = self._state.adding

        super().save(*args, **kwargs)

        self._update_agent_service_status(is_new)

    def send_automatic_message(self, delay: int = 0):
        from chats.apps.sectors.tasks import send_automatic_message

        if (
            self.user
            and self.user_assigned_at is not None
            and self.queue.sector.is_automatic_message_active
            and self.queue.sector.automatic_message_text
        ):
            send_automatic_message.apply_async(
                args=[
                    self.uuid,
                    self.queue.sector.automatic_message_text,
                    self.user.id,
                ],
                countdown=delay,
            )

    def get_permission(self, user):
        try:
            return self.queue.get_permission(user)
        except ObjectDoesNotExist:
            return None

    def can_retrieve(self, user):
        permission = self.get_permission(user)
        if not permission:
            return False
        if permission.is_admin:
            return True
        if user == self.user:
            return True

        return self.queue.is_agent(user) or self.queue.sector.is_manager(user)

    def get_is_waiting(self):
        """If the room does not have any contact message, then it is waiting"""
        check_flowstarts = self.flowstarts.filter(is_deleted=False).exists()
        return self.is_waiting or check_flowstarts

    @property
    def project(self):
        return self.queue.project

    @property
    def last_contact_message(self):
        return (
            self.messages.filter(contact__isnull=False).order_by("-created_on").first()
        )

    def trigger_default_message(self):
        default_message = self.queue.default_message
        if not default_message:
            return

        cache_key = f"room_default_message:{self.pk}"

        with get_redis_connection() as redis_connection:
            if not redis_connection.set(cache_key, "1", ex=10, nx=True):
                return

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
        if not day_validation.exists():
            return self.created_on > timezone.now() - timedelta(days=1)
        return True

    @property
    def serialized_ws_data(self):
        from chats.apps.api.v1.rooms.serializers import RoomSerializer  # noqa

        return RoomSerializer(self).data

    @property
    def last_5_messages(self):
        return (
            self.messages.exclude(text="")
            .exclude(user__isnull=True, contact__isnull=True)
            .order_by("-created_on")[:5]
        )

    def _handle_close_tags(self, tags: list):
        current_tag_ids = set(
            [str(tag_uuid) for tag_uuid in self.tags.values_list("uuid", flat=True)]
        )
        new_tag_ids = set(tags) - current_tag_ids
        tags_to_remove_ids = current_tag_ids - set([str(tag_uuid) for tag_uuid in tags])

        self.tags.add(*new_tag_ids)
        self.tags.remove(*tags_to_remove_ids)

    def close(self, tags: list = [], end_by: str = ""):
        from chats.apps.projects.usecases.status_service import InServiceStatusService

        self.is_active = False
        self.ended_at = timezone.now()
        self.ended_by = end_by

        with transaction.atomic():
            if tags is not None:
                self._handle_close_tags(tags)

            self.clear_pins()

            self.save()

        if self.user:
            project = None
            if self.queue and hasattr(self.queue, "sector"):
                sector = self.queue.sector
                if sector and hasattr(sector, "project"):
                    project = sector.project
            if project:
                InServiceStatusService.room_closed(self.user, project)

    def request_callback(self, room_data: dict):
        if self.callback_url is None:
            return None

        for attempt in range(settings.MAX_RETRIES):
            try:
                response = requests.post(
                    self.callback_url,
                    data=json.dumps(
                        {"type": "room.update", "content": room_data},
                        sort_keys=True,
                        indent=1,
                        cls=DjangoJSONEncoder,
                    ),
                    headers={"content-type": "application/json"},
                )

                if response.status_code == 404:
                    sentry_sdk.capture_message(
                        f"Callback returned 404 ERROR for URL: {self.callback_url}"
                    )
                    return None
                else:
                    response.raise_for_status()
                    return None

            except RequestException:
                if attempt < settings.MAX_RETRIES - 1:
                    delay = settings.RETRY_DELAY_SECONDS * (2**attempt)
                    time.sleep(delay)
                else:
                    raise RuntimeError(
                        f"Failed to send callback to {self.callback_url}"
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
        if not permission:
            return
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

    def can_create_discussion(self, user):
        """
        Active rooms: only admin, managers and the user on the room are able to create discussions
        Inactive rooms: anyone in the project can create discussions
        """
        if user == self.user:
            return True
        perm = self.get_permission(user)
        return not self.is_active or perm.is_manager(any_sector=True)

    def update_ticket(self):
        """
        Synchronously update ticket assignee.
        """
        if self.ticket_uuid and self.user:
            FlowRESTClient().update_ticket_assignee(self.ticket_uuid, self.user.email)

    def update_ticket_async(self):
        """
        Asynchronously update ticket assignee using Celery task.
        This method is non-blocking and provides retry functionality.
        """
        if self.ticket_uuid and self.user:
            from chats.apps.rooms.tasks import update_ticket_assignee_async

            task = update_ticket_assignee_async.delay(
                room_uuid=str(self.uuid),
                ticket_uuid=self.ticket_uuid,
                user_email=self.user.email,
            )

            logger.info(
                f"[ROOM] Launched async ticket update task - Room: {self.uuid}, "
                f"Ticket: {self.ticket_uuid}, User: {self.user.email}, "
                f"Task ID: {task.id}"
            )

            return task

    def can_pick_queue(self, user: User) -> bool:
        """
        Checks if a user can pick a room from the queue.

        If the project's routing type is QUEUE_PRIORITY, only project admins and sector managers can pick rooms.
        Otherwise, any user with queue access can pick rooms.

        Args:
            user (User): The user attempting to pick from queue

        Returns:
            bool: Whether the user can pick from queue
        """
        queue: "Queue" = self.queue
        project: "Project" = self.queue.sector.project

        if not project.room_routing_type == RoomRoutingType.QUEUE_PRIORITY:
            return True

        is_project_admin = project.is_admin(user)
        is_sector_manager = queue.sector.is_manager(user)

        return is_project_admin or is_sector_manager

    @property
    def imported_history_url(self):
        if self.contact and self.contact.imported_history_url:
            return self.contact.imported_history_url
        return None

    def pin(self, user: User):
        """
        Pins a room for a user.
        """

        if self.pins.filter(user=user).exists():
            return

        if (
            RoomPin.objects.filter(
                user=user,
                room__queue__sector__project=self.queue.sector.project,
                room__is_active=True,
            ).count()
            >= settings.MAX_ROOM_PINS_LIMIT
        ):
            raise MaxPinRoomLimitReachedError

        if self.user != user:
            raise PermissionDenied

        if not self.is_active:
            raise RoomIsNotActiveError

        return RoomPin.objects.create(room=self, user=user)

    def unpin(self, user: User):
        """
        Unpins a room for a user.
        """
        if self.user != user:
            raise PermissionDenied

        return self.pins.filter(user=user).delete()

    def clear_pins(self):
        """
        Clears all pins for a room.
        """
        return self.pins.all().delete()

    def add_transfer_to_history(self, transfer: dict):
        """
        Adds a transfer to the full transfer history.
        """
        self.full_transfer_history.append(transfer)
        self.transfer_history = transfer  # legacy
        self.save(update_fields=["full_transfer_history", "transfer_history"])


class RoomPin(BaseModel):
    """
    A room pin is a record of a user pinning a room.
    """

    room = models.ForeignKey(
        "rooms.Room",
        related_name="pins",
        verbose_name=_("room"),
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "accounts.User",
        related_name="room_pins",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
    )
    created_on = models.DateTimeField(_("created on"), auto_now_add=True)

    class Meta:
        verbose_name = _("Room Pin")
        verbose_name_plural = _("Room Pins")
        constraints = [
            models.UniqueConstraint(
                fields=["room", "user"],
                name="unique_room_user_room_pin",
            )
        ]


class RoomNote(BaseModel):
    """
    Internal notes for rooms that can be created by agents
    """

    room = models.ForeignKey(
        "rooms.Room",
        related_name="notes",
        verbose_name=_("room"),
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "accounts.User",
        related_name="room_notes",
        verbose_name=_("user"),
        on_delete=models.CASCADE,
    )
    text = models.TextField(_("text"))
    is_deletable = models.BooleanField(_("is deletable"), default=True)
    message = models.OneToOneField(
        "msgs.Message",
        related_name="internal_note",
        verbose_name=_("message"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Room Note")
        verbose_name_plural = _("Room Notes")
        ordering = ["-created_on"]

    @property
    def serialized_ws_data(self):
        """
        Return serialized data for WebSocket notifications
        """
        return {
            "uuid": str(self.uuid),
            "room": str(self.room.uuid),
            "user": {"uuid": str(self.user.pk), "name": self.user.name},
            "text": self.text,
            "created_on": self.created_on.isoformat(),
            "is_deletable": self.is_deletable,
        }

    def notify_websocket(self, action):
        """
        Send WebSocket notification for note actions
        """
        if action == "create":
            event_name = "room_note.create"
            content = self.serialized_ws_data
        elif action == "delete":
            event_name = "room_note.delete"
            content = {"uuid": str(self.uuid), "room": str(self.room.uuid)}
        else:
            return

        # Send to room group
        send_channels_group(
            group_name=f"room_{self.room.uuid}",
            call_type="notify",
            content=content,
            action=event_name,
        )

        # Send to queue or user permission group
        if self.room.user:
            permission = self.room.get_permission(self.room.user)
            if permission:
                send_channels_group(
                    group_name=f"permission_{permission.pk}",
                    call_type="notify",
                    content=content,
                    action=event_name,
                )
        elif self.room.queue:
            send_channels_group(
                group_name=f"queue_{self.room.queue.pk}",
                call_type="notify",
                content=content,
                action=event_name,
            )

    def delete(self, *args, **kwargs):
        """
        Ensure the associated blank message is also removed when deleting the note
        """
        msg = self.message
        super().delete(*args, **kwargs)
        if msg:
            msg.delete()
