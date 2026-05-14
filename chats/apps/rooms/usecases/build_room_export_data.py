"""Builds the data contract used to render room export documents (HTML/PDF).

The output dict is the contract negotiated with the template author: any change
here must be reflected in the template and vice-versa.
"""

from datetime import timedelta
from typing import TYPE_CHECKING, Optional

from chats.apps.accounts.models import User

if TYPE_CHECKING:
    from chats.apps.msgs.models import Message
    from chats.apps.rooms.models import Room, RoomNote


SENDER_TYPE_AGENT = "agent"
SENDER_TYPE_CONTACT = "contact"
SENDER_TYPE_BOT = "bot"

TIMELINE_ITEM_MESSAGE = "message"
TIMELINE_ITEM_INTERNAL_NOTE = "internal_note"
TIMELINE_ITEM_TRANSFER_CHIP = "transfer_chip"


def _is_feedback_message(message: "Message") -> bool:
    """Detects auto-generated transfer feedback messages that should be hidden.

    These messages store the transfer payload as JSON text and would duplicate
    the transfer_chip entries derived from full_transfer_history.
    """
    text = (message.text or "").strip()
    return text.startswith('{"method"') or text.startswith('{"content"')


def _detect_sender_type(message: "Message") -> str:
    if message.user_id and not message.contact_id:
        return SENDER_TYPE_AGENT
    if message.contact_id and not message.user_id:
        return SENDER_TYPE_CONTACT
    return SENDER_TYPE_BOT


def _resolve_sender_name(message: "Message") -> Optional[str]:
    if message.user_id:
        if message.user:
            return message.user.first_name or message.user.email
        return message.user_id
    if message.contact_id:
        if message.contact:
            return message.contact.name or message.contact.external_id
        return None
    return SENDER_TYPE_BOT


def _build_media_entry(media) -> dict:
    file_url = None
    if media.media_file:
        try:
            file_url = media.media_file.url
        except Exception:
            file_url = None
    return {
        "content_type": media.content_type,
        "url": media.media_url or file_url,
        "data_uri": None,
    }


class BuildRoomExportData:
    """Builds the dict consumed by the room export template."""

    def execute(self, room: "Room") -> dict:
        room_block = self._build_room_block(room)
        contact_block = self._build_contact_block(room)
        agents_block = self._build_agents_block(room)
        timeline = self._build_timeline(room)

        return {
            "room": room_block,
            "contact": contact_block,
            "agents": agents_block,
            "timeline": timeline,
        }

    def _build_room_block(self, room: "Room") -> dict:
        return {
            "uuid": str(room.uuid),
            "protocol": room.protocol,
            "started_at": room.created_on,
            "ended_at": room.ended_at,
            "ended_by": room.ended_by,
            "tags": list(room.tags.values_list("name", flat=True)),
            "custom_fields": room.custom_fields or {},
        }

    def _build_contact_block(self, room: "Room") -> dict:
        contact = room.contact
        if not contact:
            return {
                "name": None,
                "email": None,
                "phone": None,
                "external_id": None,
                "custom_fields": {},
            }
        return {
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "external_id": contact.external_id,
            "custom_fields": contact.custom_fields or {},
        }

    def _build_agents_block(self, room: "Room") -> list[dict]:
        emails: set[str] = set()

        message_emails = room.messages.filter(user__isnull=False).values_list(
            "user__email", flat=True
        )
        for email in message_emails:
            if email:
                emails.add(email)

        for entry in room.full_transfer_history or []:
            to = entry.get("to") or {}
            if to.get("type") == "user" and to.get("email"):
                emails.add(to["email"])

        current_email = room.user.email if room.user_id and room.user else None
        if current_email:
            emails.add(current_email)

        if not emails:
            return []

        users = User.objects.filter(email__in=emails)
        return [
            {
                "email": user.email,
                "name": user.first_name or user.email,
                "is_current": user.email == current_email,
            }
            for user in users
        ]

    def _build_timeline(self, room: "Room") -> list[dict]:
        items: list[dict] = []
        items.extend(self._build_message_items(room))
        items.extend(self._build_note_items(room))
        items.extend(self._build_transfer_chip_items(room))
        items.sort(key=lambda item: item["created_on"])
        return items

    def _build_message_items(self, room: "Room") -> list[dict]:
        queryset = (
            room.messages.all()
            .select_related("user", "contact")
            .prefetch_related("medias")
        )
        items = []
        for message in queryset:
            if _is_feedback_message(message):
                continue
            items.append(
                {
                    "type": TIMELINE_ITEM_MESSAGE,
                    "sender_type": _detect_sender_type(message),
                    "sender_name": _resolve_sender_name(message),
                    "created_on": message.created_on,
                    "text": message.text,
                    "medias": [
                        _build_media_entry(media) for media in message.medias.all()
                    ],
                }
            )
        return items

    def _build_note_items(self, room: "Room") -> list[dict]:
        queryset = room.notes.all().select_related("user")
        items = []
        for note in queryset:
            items.append(
                {
                    "type": TIMELINE_ITEM_INTERNAL_NOTE,
                    "sender_name": self._resolve_note_author_name(note),
                    "created_on": note.created_on,
                    "text": note.text,
                    "anchored_message_uuid": (
                        str(note.message.uuid) if note.message_id else None
                    ),
                }
            )
        return items

    def _resolve_note_author_name(self, note: "RoomNote") -> Optional[str]:
        if not note.user:
            return None
        return note.user.first_name or note.user.email

    def _build_transfer_chip_items(self, room: "Room") -> list[dict]:
        history = room.full_transfer_history or []
        if not history:
            return []

        timestamps = self._distribute_chip_timestamps(room, len(history))

        items = []
        for index, entry in enumerate(history):
            items.append(
                {
                    "type": TIMELINE_ITEM_TRANSFER_CHIP,
                    "kind": entry.get("action"),
                    "from": entry.get("from"),
                    "to": entry.get("to"),
                    "by": entry.get("requested_by"),
                    "created_on": timestamps[index],
                }
            )
        return items

    def _distribute_chip_timestamps(self, room: "Room", count: int) -> list:
        """Approximates timestamps for transfer chips.

        full_transfer_history doesn't store per-entry timestamps, so chips are
        distributed evenly between room.created_on and room.ended_at to keep
        the timeline ordering consistent. If ended_at is missing, chips are
        spaced by 1 second.
        """
        if room.ended_at and room.ended_at > room.created_on:
            span = room.ended_at - room.created_on
            return [
                room.created_on + (span * (i + 1) / (count + 1)) for i in range(count)
            ]
        return [room.created_on + timedelta(seconds=i) for i in range(count)]


__all__ = ["BuildRoomExportData"]
