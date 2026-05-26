"""
Inactivity usecase.

Responsibilities:
- `warn_inactive_rooms`  : find rooms whose contact has not replied within the
  configured warning timeout and send the warning message.
- `close_inactive_rooms` : find rooms already warned that exceeded the closure
  timeout and close them automatically.
- `reset_inactivity`     : clear the inactive flag when the contact replies.
"""

import logging
from typing import TYPE_CHECKING, Optional

from django.db import transaction
from django.utils import timezone
from sentry_sdk import capture_exception

from chats.apps.msgs.models import Message
from chats.apps.rooms.models import Room

if TYPE_CHECKING:
    from chats.apps.accounts.models import User


logger = logging.getLogger(__name__)


INACTIVITY_END_BY = "inactivity"


def _send_silent_automatic_message(
    room: "Room", text: str, user: Optional["User"]
) -> Optional[Message]:
    """
    Creates an automatic message on the room WITHOUT updating
    `last_interaction` / `last_message_*` fields.

    The inactivity feature requires that the warning and closure messages do
    not reset the inactivity counter, so they can't go through the regular
    `room.update_last_message` flow.
    """
    if not text:
        return None

    try:
        with transaction.atomic():
            message = Message.objects.create(
                room=room,
                text=text,
                user=user,
                contact=None,
            )
            transaction.on_commit(lambda: message.notify_room("create", True))
            return message
    except Exception as exc:
        logger.error(
            "[INACTIVITY] Failed to send silent automatic message to room %s: %s",
            room.pk,
            exc,
            exc_info=True,
        )
        capture_exception(exc)
        return None


def _eligible_warn_queryset():
    """
    Base queryset for rooms that may need an inactivity warning.

    Filters cover the rules from the spec:
    - room is open and assigned to an agent (not in queue);
    - not currently flagged as inactive;
    - not waiting for a flow start;
    - the agent was the last one to talk (`last_message_user` populated).

    The final timeout comparison happens in Python because the timeout value
    lives inside the sector's JSON config and varies per sector.
    """
    return Room.objects.filter(
        is_active=True,
        is_inactive=False,
        is_waiting=False,
        user__isnull=False,
        last_message_user__isnull=False,
    ).select_related("queue__sector", "user")


def _eligible_close_queryset():
    """
    Base queryset for rooms that already received the warning and may need to
    be closed for inactivity.
    """
    return Room.objects.filter(
        is_active=True,
        is_inactive=True,
        is_waiting=False,
        user__isnull=False,
        last_message_user__isnull=False,
    ).select_related("queue__sector", "user")


def _read_inactivity_config(room: "Room") -> Optional[dict]:
    try:
        return room.queue.sector.inactivity_timeout
    except AttributeError:
        return None


class InactivityService:
    """
    Encapsulates the inactivity flow. Stateless; safe to instantiate per call.
    """

    def warn_inactive_rooms(self) -> int:
        """
        Sends inactivity warnings to all eligible rooms.

        Returns the number of rooms that were warned.
        """
        now = timezone.now()
        warned = 0

        for room in _eligible_warn_queryset().iterator():
            config = _read_inactivity_config(room)

            if not config or not config.get("is_message_timeout_enabled"):
                continue

            timeout = config.get("message_timeout_time") or 0
            if timeout <= 0:
                continue

            if not room.last_interaction:
                continue

            elapsed = (now - room.last_interaction).total_seconds()
            if elapsed < timeout:
                continue

            if self._warn_room(room, config):
                warned += 1

        logger.info("[INACTIVITY] Warned %s rooms", warned)
        return warned

    def close_inactive_rooms(self) -> int:
        """
        Closes all rooms that exceeded the closure timeout after the warning.

        Returns the number of rooms that were closed.
        """
        now = timezone.now()
        closed = 0

        for room in _eligible_close_queryset().iterator():
            config = _read_inactivity_config(room)

            if not config or not config.get("is_close_room_enabled"):
                continue

            warn_timeout = config.get("message_timeout_time") or 0
            close_timeout = config.get("close_room_timeout_time") or 0
            if warn_timeout <= 0 or close_timeout <= 0:
                continue

            if not room.last_interaction:
                continue

            elapsed = (now - room.last_interaction).total_seconds()
            if elapsed < (warn_timeout + close_timeout):
                continue

            if self._close_room(room, config):
                closed += 1

        logger.info("[INACTIVITY] Closed %s rooms", closed)
        return closed

    def reset_inactivity(self, room: "Room") -> bool:
        """
        Clears the `is_inactive` flag for the given room and notifies the
        websocket consumers. Should be called when the contact replies on a
        room currently flagged as inactive.

        Returns True if the flag was cleared, False otherwise (already clear,
        room closed, etc.).
        """
        if not room.is_active or not room.is_inactive:
            return False

        Room.objects.filter(pk=room.pk, is_active=True).update(is_inactive=False)
        room.is_inactive = False

        try:
            room.notify_inactivity()
        except Exception as exc:
            logger.warning(
                "[INACTIVITY] Failed to notify websocket on reset for room %s: %s",
                room.pk,
                exc,
            )

        return True

    def _warn_room(self, room: "Room", config: dict) -> bool:
        text = config.get("message_timeout_text") or ""

        message = _send_silent_automatic_message(room, text, room.user)
        if message is None and text:
            return False

        Room.objects.filter(pk=room.pk, is_inactive=False, is_active=True).update(
            is_inactive=True
        )
        room.is_inactive = True

        try:
            room.notify_inactivity()
        except Exception as exc:
            logger.warning(
                "[INACTIVITY] Failed to notify websocket on warn for room %s: %s",
                room.pk,
                exc,
            )

        logger.info("[INACTIVITY] Warned room %s", room.pk)
        return True

    def _close_room(self, room: "Room", config: dict) -> bool:
        text = config.get("close_room_message_text") or ""

        _send_silent_automatic_message(room, text, room.user)

        try:
            room.close(end_by=INACTIVITY_END_BY)
        except Exception as exc:
            logger.error(
                "[INACTIVITY] Failed to close room %s: %s",
                room.pk,
                exc,
                exc_info=True,
            )
            capture_exception(exc)
            return False

        logger.info("[INACTIVITY] Closed room %s", room.pk)
        return True
