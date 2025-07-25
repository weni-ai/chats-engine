from datetime import datetime

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.utils import timezone
from rest_framework import serializers

from chats.apps.accounts.models import User
from chats.apps.ai_features.history_summary.models import (
    HistorySummary,
    HistorySummaryFeedback,
)
from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactRelationsSerializer
from chats.apps.api.v1.msgs.serializers import MessageSerializer
from chats.apps.api.v1.queues.serializers import QueueSerializer
from chats.apps.api.v1.sectors.serializers import DetailSectorTagSerializer
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room, RoomPin


class RoomMessageStatusSerializer(serializers.Serializer):
    seen = serializers.BooleanField(required=False, default=True)
    messages = serializers.ListField(
        child=serializers.CharField(required=False),
        max_length=200,
        allow_empty=True,
        default=[],
    )


class RoomSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    contact = ContactRelationsSerializer(many=False, read_only=True)
    queue = QueueSerializer(many=False, read_only=True)
    tags = DetailSectorTagSerializer(many=True, read_only=True)
    unread_msgs = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    is_waiting = serializers.SerializerMethodField()
    linked_user = serializers.SerializerMethodField()
    is_24h_valid = serializers.SerializerMethodField()
    flowstart_data = serializers.SerializerMethodField()
    last_interaction = serializers.DateTimeField(read_only=True)
    can_edit_custom_fields = serializers.SerializerMethodField()
    config = serializers.JSONField(required=False, read_only=True)
    imported_history_url = serializers.CharField(read_only=True, default="")
    full_transfer_history = serializers.JSONField(
        required=False, read_only=True, default=list
    )

    class Meta:
        model = Room
        fields = "__all__"
        read_only_fields = [
            "created_on",
            "ended_at",
            "custom_fields",
            "urn",
            "linked_user",
            "is_24h_valid",
            "last_interaction",
            "can_edit_custom_fields",
            "imported_history_url",
            "full_transfer_history",
        ]

    def get_is_24h_valid(self, room: Room) -> bool:
        return room.is_24h_valid

    def get_flowstart_data(self, room: Room) -> bool:
        try:
            flowstart = room.flowstarts.get(is_deleted=False)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            return {}
        return {
            "name": flowstart.name,
            "is_deleted": flowstart.is_deleted,
            "created_on": flowstart.created_on,
        }

    def get_linked_user(self, room: Room):
        try:
            return room.contact.get_linked_user(room.queue.sector.project).full_name
        except AttributeError:
            return ""

    def get_is_waiting(self, room: Room):
        return room.get_is_waiting()

    def get_unread_msgs(self, room: Room):
        return room.messages.filter(seen=False).count()

    def get_last_message(self, room: Room):
        last_message = (
            room.messages.order_by("-created_on")
            .exclude(user__isnull=True, contact__isnull=True)
            .first()
        )

        if not last_message:
            return None

        return MessageSerializer(last_message).data

    def get_can_edit_custom_fields(self, room: Room):
        return room.queue.sector.can_edit_custom_fields


class ListRoomSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    queue = serializers.SerializerMethodField()
    unread_msgs = serializers.IntegerField(required=False, default=0)
    last_message = serializers.SerializerMethodField()
    is_waiting = serializers.BooleanField()
    is_24h_valid = serializers.BooleanField(
        default=True, source="is_24h_valid_computed"
    )
    config = serializers.JSONField(required=False, read_only=True)
    last_interaction = serializers.DateTimeField(read_only=True)
    can_edit_custom_fields = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(default=True)
    imported_history_url = serializers.CharField(read_only=True, default="")
    is_pinned = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "uuid",
            "user",
            "queue",
            "contact",
            "unread_msgs",
            "last_message",
            "is_waiting",
            "is_24h_valid",
            "last_interaction",
            "can_edit_custom_fields",
            "custom_fields",
            "urn",
            "transfer_history",
            "protocol",
            "service_chat",
            "is_active",
            "config",
            "imported_history_url",
            "is_pinned",
        ]

    def get_user(self, room: Room):
        try:
            return {
                "first_name": room.user.first_name,
                "last_name": room.user.last_name,
                "email": room.user.email,
            }
        except AttributeError:
            return None

    def get_queue(self, room: Room):
        try:
            return {
                "uuid": str(room.queue.uuid),
                "name": room.queue.name,
                "sector": str(room.queue.sector.uuid),
                "sector_name": room.queue.sector.name,
            }
        except AttributeError:
            return None

    def get_contact(self, room: Room):
        return {
            "uuid": room.contact.uuid,
            "name": room.contact.name,
            "external_id": room.contact.external_id,
        }

    def get_can_edit_custom_fields(self, room: Room):
        return room.queue.sector.can_edit_custom_fields

    def get_last_message(self, room: Room):
        last_message = (
            room.messages.order_by("-created_on")
            .exclude(user__isnull=True, contact__isnull=True)
            .first()
        )

        return MessageSerializer(last_message).data

    def get_is_pinned(self, room: Room) -> bool:
        request = self.context.get("request")

        if not request:
            return False

        return RoomPin.objects.filter(room=room, user=request.user).exists()


class TransferRoomSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=False, read_only=True)
    user_email = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        required=False,
        source="user",
        slug_field="email",
        write_only=True,
        allow_null=True,
    )
    queue_uuid = serializers.PrimaryKeyRelatedField(
        queryset=Queue.objects.all(), required=False, source="queue", write_only=True
    )
    queue = QueueSerializer(many=False, required=False, read_only=True)
    contact = ContactRelationsSerializer(many=False, required=False, read_only=True)
    tags = DetailSectorTagSerializer(many=True, required=False, read_only=True)
    linked_user = serializers.SerializerMethodField()
    imported_history_url = serializers.CharField(read_only=True, default="")

    class Meta:
        model = Room
        exclude = ["callback_url"]
        read_only_fields = [
            "uuid",
            "user",
            "queue",
            "contact",
            "ended_at",
            "is_active",
            "custom_fields",
            "transfer_history",
            "tags",
            "ended_by",
            "urn",
            "linked_user",
            "imported_history_url",
        ]

        extra_kwargs = {
            "queue": {"required": False, "read_only": True, "allow_null": False},
            "contact": {"required": False, "read_only": True, "allow_null": False},
            "user": {"required": False, "read_only": True, "allow_null": False},
        }

    def get_linked_user(self, room: Room):
        try:
            return room.contact.get_linked_user(room.queue.sector.project).full_name
        except AttributeError:
            return ""


class RoomContactSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    queue = QueueSerializer(many=False, read_only=True)
    tags = DetailSectorTagSerializer(many=True, read_only=True)
    is_waiting = serializers.SerializerMethodField()
    linked_user = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "user",
            "queue",
            "tags",
            "created_on",
            "ended_at",
            "custom_fields",
            "urn",
            "is_waiting",
            "linked_user",
        ]

    def get_linked_user(self, room: Room):
        try:
            return room.contact.get_linked_user(room.queue.sector.project).full_name
        except AttributeError:
            return ""

    def get_is_waiting(self, room: Room):
        return room.get_is_waiting()


class RoomInfoSerializer(serializers.ModelSerializer):
    first_user_message_sent_at = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "uuid",
            "user",
            "first_user_message_sent_at",
            "user_assigned_at",
        ]

    def get_user(self, room: Room) -> dict:
        user: User = room.user

        if not user:
            return None

        name = f"{user.first_name} {user.last_name}".strip()

        return {"email": user.email, "name": name}

    def get_first_user_message_sent_at(self, room: Room) -> datetime:
        if (
            first_user_message := room.messages.filter(user__isnull=False)
            .order_by("created_on")
            .first()
        ):
            return first_user_message.created_on

        return None


class RoomHistorySummarySerializer(serializers.ModelSerializer):
    feedback = serializers.SerializerMethodField()

    class Meta:
        model = HistorySummary
        fields = ["status", "summary", "feedback"]

    def get_feedback(self, history_summary: HistorySummary) -> dict:
        feedback = history_summary.feedbacks.filter(
            user=self.context["request"].user
        ).first()

        if feedback:
            return {
                "liked": feedback.liked,
            }

        return {
            "liked": None,
        }


class RoomHistorySummaryFeedbackSerializer(serializers.ModelSerializer):
    text = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=150
    )

    class Meta:
        model = HistorySummaryFeedback
        fields = ["liked", "text"]

    def validate(self, attrs):
        attrs["user"] = self.context["request"].user
        attrs["history_summary"] = self.context["history_summary"]

        if not attrs.get("text"):
            attrs["text"] = None

        return super().validate(attrs)


class RoomsReportFiltersSerializer(serializers.Serializer):
    """
    Filters for the rooms report.
    """

    created_on__gte = serializers.DateTimeField(required=True)
    created_on__lte = serializers.DateTimeField(required=False)
    tags = serializers.ListField(required=False, child=serializers.UUIDField())

    def validate(self, attrs):
        created_on__gte = attrs.get("created_on__gte")
        created_on__lte = attrs.get("created_on__lte")

        if created_on__gte and created_on__lte:
            if created_on__gte > created_on__lte:
                raise serializers.ValidationError(
                    "created_on__gte must be before created_on__lte"
                )

        start = created_on__gte
        end = created_on__lte or timezone.now()

        period = (end - start).days

        if period > 90:
            raise serializers.ValidationError("Period must be less than 90 days")

        if tags := attrs.pop("tags", None):
            attrs["tags__in"] = tags

        return super().validate(attrs)


class RoomsReportSerializer(serializers.Serializer):
    """
    Serializer for the rooms report.
    """

    recipient_email = serializers.EmailField(required=True)
    filters = RoomsReportFiltersSerializer(required=True)


class PinRoomSerializer(serializers.Serializer):
    """
    Serializer for the pin room.
    """

    # True to pin, False to unpin
    status = serializers.BooleanField(required=True)
