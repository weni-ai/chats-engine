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

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from sentry_sdk import capture_exception
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

from chats.apps.msgs.models import AutomaticMessage, AutomaticMessageType, Message
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.models import Room

if TYPE_CHECKING:
    from chats.apps.accounts.models import User


logger = logging.getLogger(__name__)


INACTIVITY_END_BY = "inactivity"


def _get_room_project_uuid(room: "Room") -> Optional[str]:
    """
    Extracts the project UUID from a room safely. Returns None when the
    related sector/project chain is missing (defensive — not expected in
    eligible rooms).
    """
    try:
        return str(room.queue.sector.project.uuid)
    except AttributeError:
        return None


def is_inactivity_feature_active(project_uuid: Optional[str]) -> bool:
    """
    Evaluates the inactivity feature flag (`weniChatsInactivityTimeout`)
    for the given project. Returns False on missing project or if the
    feature flag service raises, so a flag outage never closes/warns
    rooms unexpectedly.
    """
    if not project_uuid:
        return False

    try:
        return is_feature_active_for_attributes(
            settings.WENI_CHATS_INACTIVITY_TIMEOUT_FLAG_KEY,
            {"projectUUID": project_uuid},
        )
    except Exception as exc:
        logger.warning(
            "[INACTIVITY] Failed to evaluate feature flag for project %s: %s",
            project_uuid,
            exc,
        )
        capture_exception(exc)
        return False


def _send_silent_automatic_message(
    room: "Room",
    text: str,
    user: Optional["User"],
    message_type: Optional[str] = None,
) -> Optional[Message]:
    """
    Creates an automatic message on the room WITHOUT updating
    `last_interaction` / `last_message_*` fields.

    The inactivity feature requires that the warning and closure messages do
    not reset the inactivity counter, so they can't go through the regular
    `room.update_last_message` flow.

    `message_type` classifies the automatic message (e.g. `inactive_warning`
    or `inactive_close`) so the front can render a specific UI for each.
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
            if message_type is not None:
                AutomaticMessage.objects.create(
                    message=message,
                    room=room,
                    automatic_message_type=message_type,
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
    - the agent was the last one to talk (`last_message_user` populated);
    - the sector has the inactivity warning feature enabled (so we don't
      pull rooms from sectors that won't be processed anyway).

    The final timeout comparison happens in Python because the timeout value
    lives inside the sector's JSON config and varies per sector.
    """
    return Room.objects.filter(
        is_active=True,
        is_inactive=False,
        is_waiting=False,
        user__isnull=False,
        last_message_user__isnull=False,
        last_message__automatic_message__isnull=True,
        queue__sector__inactivity_timeout__is_message_timeout_enabled=True,
    ).select_related("queue__sector", "user")


def _eligible_close_queryset():
    """
    Base queryset for rooms that already received the warning and may need to
    be closed for inactivity.

    Restricted to sectors with the automatic closure feature enabled, so the
    database does not have to return rooms from sectors that won't be closed.
    """
    return Room.objects.filter(
        is_active=True,
        is_inactive=True,
        is_waiting=False,
        user__isnull=False,
        last_message_user__isnull=False,
        queue__sector__inactivity_timeout__is_close_room_enabled=True,
    ).exclude(
        last_message__automatic_message__automatic_message_type=(
            AutomaticMessageType.AUTOMATIC_OPEN
        ),
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

    def __init__(self) -> None:
        # Per-instance cache to avoid re-evaluating the feature flag for the
        # same project on every room when iterating large querysets.
        self._feature_flag_cache: dict[str, bool] = {}

    def _is_feature_active_for_room(self, room: "Room") -> bool:
        project_uuid = _get_room_project_uuid(room)
        if not project_uuid:
            return False

        if project_uuid in self._feature_flag_cache:
            return self._feature_flag_cache[project_uuid]

        active = is_inactivity_feature_active(project_uuid)
        self._feature_flag_cache[project_uuid] = active
        return active

    def warn_inactive_rooms(self) -> int:
        """
        Sends inactivity warnings to all eligible rooms.

        Returns the number of rooms that were warned.
        """
        now = timezone.now()
        warned = 0

        for room in _eligible_warn_queryset().iterator():
            if not self._is_feature_active_for_room(room):
                continue

            config = _read_inactivity_config(room) or {}

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
            if not self._is_feature_active_for_room(room):
                continue

            config = _read_inactivity_config(room) or {}

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

        if not self._is_feature_active_for_room(room):
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

        message = _send_silent_automatic_message(
            room,
            text,
            room.user,
            message_type=AutomaticMessageType.INACTIVE_WARNING,
        )
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

        # Order matters: both messages must be created BEFORE `room.close()`
        # because `Message.save()` rejects writes to inactive rooms.
        # 1) Human-facing closure text (only when configured).
        # 2) System feedback (`rc` / `automatic_close`) — always emitted.
        _send_silent_automatic_message(
            room,
            text,
            room.user,
            message_type=AutomaticMessageType.INACTIVE_CLOSE,
        )

        try:
            self._create_automatic_close_feedback(room)
        except Exception as exc:
            # Feedback failure should not block the actual closure; log and
            # keep going so the room still closes.
            logger.warning(
                "[INACTIVITY] Failed to create close feedback for room %s: %s",
                room.pk,
                exc,
            )
            capture_exception(exc)

        # Mark `automatic_closed=True` BEFORE `room.close()` so the flag is
        # persisted in the same `save()` call and visible to any post-close
        # signal/consumer.
        room.automatic_closed = True

        try:
            room.close(end_by=INACTIVITY_END_BY, closed_by=room.user)
        except Exception as exc:
            logger.error(
                "[INACTIVITY] Failed to close room %s: %s",
                room.pk,
                exc,
                exc_info=True,
            )
            capture_exception(exc)
            return False

        # Notify the websocket groups that the room was closed, mirroring the
        # manual close endpoint, so the front removes it from the agent's list
        # in real time (and the room callback is triggered).
        try:
            room.notify_queue("close", callback=True)
            room.notify_user("close")
        except Exception as exc:
            logger.warning(
                "[INACTIVITY] Failed to notify websocket on close for room %s: %s",
                room.pk,
                exc,
            )
            capture_exception(exc)

        # The manual close endpoint computes service metrics
        # (interaction_time, message_response_time, etc.) in the view via
        # `close_room`. The automatic close must replicate it, otherwise
        # inactivity-closed rooms are left without those metrics.
        if settings.ACTIVATE_CALC_METRICS:
            try:
                from chats.apps.rooms.views import close_room

                close_room(str(room.pk))
            except Exception as exc:
                logger.warning(
                    "[INACTIVITY] Failed to generate metrics for room %s: %s",
                    room.pk,
                    exc,
                )
                capture_exception(exc)

        # Closing a room frees up the agent's capacity, so re-run the queue
        # priority routing to assign any waiting room. The manual close
        # endpoint does this in the view; the automatic close must too.
        if room.queue:
            try:
                from chats.apps.queues.utils import start_queue_priority_routing

                start_queue_priority_routing(room.queue)
            except Exception as exc:
                logger.warning(
                    "[INACTIVITY] Failed to start queue priority routing "
                    "for room %s: %s",
                    room.pk,
                    exc,
                )
                capture_exception(exc)

        logger.info("[INACTIVITY] Closed room %s", room.pk)
        return True

    def _create_automatic_close_feedback(self, room: "Room") -> None:
        """
        Creates the `rc` / `automatic_close` feedback message on the room.
        Must be called while the room is still active (`Message.save()`
        rejects writes to inactive rooms). Imports the helper lazily to
        mirror the pattern used elsewhere (e.g. `chats.apps.queues.utils`)
        and avoid potential circular imports.
        """
        from chats.apps.rooms.views import create_room_feedback_message

        create_room_feedback_message(
            room,
            {"action": "automatic_close"},
            method=RoomFeedbackMethods.ROOM_CLOSE,
        )
