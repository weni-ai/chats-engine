from typing import Optional
from rest_framework import serializers
from django.utils import timezone

from chats.apps.msgs.models import Message
from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.rooms.models import RoomNote


class ArchiveUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "name",
        ]


class ArchiveContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "name",
            "external_id",
        ]


class ArchiveMessageSerializer(serializers.ModelSerializer):
    user = ArchiveUserSerializer(read_only=True)
    contact = ArchiveContactSerializer(read_only=True)
    created_on = serializers.SerializerMethodField(read_only=True)
    internal_note = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Message
        fields = [
            "uuid",
            "text",
            "created_on",
            "user",
            "contact",
            "is_automatic_message",
            "internal_note",
        ]

    def get_created_on(self, obj) -> str:
        # Ensure the datetime is timezone-aware and convert to UTC
        if timezone.is_naive(obj.created_on):
            dt = timezone.make_aware(obj.created_on, timezone.utc)
        else:
            dt = obj.created_on.astimezone(timezone.utc)

        return dt.isoformat()

    def get_internal_note(self, obj: Message) -> Optional[dict]:
        internal_note: RoomNote = getattr(obj, "internal_note", None)

        if internal_note:
            return {
                "uuid": str(internal_note.uuid),
                "text": internal_note.text,
            }

        return None
