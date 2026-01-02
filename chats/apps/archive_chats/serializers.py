from rest_framework import serializers
from django.utils import timezone

from chats.apps.archive_chats.dataclass import ArchiveMessageMedia
from chats.apps.msgs.models import Message
from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact


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


class ArchiveMessageMediaSerializer(serializers.Serializer):
    url = serializers.URLField(read_only=True)
    content_type = serializers.CharField(read_only=True)


class ArchiveMessageSerializer(serializers.ModelSerializer):
    user = ArchiveUserSerializer(read_only=True)
    contact = ArchiveContactSerializer(read_only=True)
    created_on = serializers.SerializerMethodField(read_only=True)
    media = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Message
        fields = [
            "uuid",
            "text",
            "created_on",
            "user",
            "contact",
            "media",
        ]

    def get_created_on(self, obj) -> str:
        # Ensure the datetime is timezone-aware and convert to UTC
        if timezone.is_naive(obj.created_on):
            dt = timezone.make_aware(obj.created_on, timezone.utc)
        else:
            dt = obj.created_on.astimezone(timezone.utc)

        return dt.isoformat()

    def get_media(self, obj) -> list[dict]:
        media: list[ArchiveMessageMedia] = self.context.get("media", [])

        return ArchiveMessageMediaSerializer(media, many=True).data
