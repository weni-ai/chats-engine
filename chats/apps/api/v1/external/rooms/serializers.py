import pendulum
from typing import Dict, List

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from chats.apps.accounts.models import User
from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactRelationsSerializer
from chats.apps.api.v1.queues.serializers import QueueSerializer
from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.rooms.views import close_room


def get_active_room_flow_start(contact, flow_uuid, project):
    query_filters = {
        "references__external_id": contact.external_id,
        "flow": flow_uuid,
        "room__isnull": False,
        "is_deleted": False,
    }
    flow_start = (
        project.flowstarts.filter(**query_filters).order_by("-created_on").first()
    )
    try:
        if flow_start.room.is_active is True:
            flow_start.is_deleted = True
            flow_start.save()
            return flow_start.room
    except AttributeError:
        config = project.config or {}

        if config.get("ignore_close_rooms_on_flow_start", False):
            return None

        # if create new room, but there's a room flowstart to another flow, close the room and the flowstart

        query_filters.pop("flow")
        flowstarts = project.flowstarts.filter(**query_filters)

        for fs in flowstarts:
            fs.is_deleted = True
            fs.save()
            room = fs.room
            if room.is_active:
                room.close([], "new_room")
                close_room(str(room.pk))
        return None
    return None


def get_room_user(
    contact: Contact,
    queue: Queue,
    user: User,
    groups: List[Dict[str, str]],
    is_created: bool,
    flow_uuid,
    project,
):
    # User that started the flow, if any
    reference_filter = [group["uuid"] for group in groups]
    reference_filter.append(contact.external_id)
    query_filters = {"references__external_id__in": reference_filter}
    if flow_uuid:
        query_filters["flow"] = flow_uuid

    last_flow_start = (
        project.flowstarts.order_by("-created_on").filter(**query_filters).first()
    )

    if last_flow_start:
        if is_created is True or not contact.rooms.filter(
            queue__sector__project=project, created_on__gt=last_flow_start.created_on
        ):
            if last_flow_start.permission.status == "ONLINE":
                return last_flow_start.permission.user

    # User linked to the contact
    if not is_created:
        linked_user = contact.get_linked_user(project)
        if linked_user is not None and linked_user.is_online:
            return linked_user.user

    # Online user on the queue
    if not user:
        return queue.available_agents.first() or None
    permission = project.permissions.filter(user=user, status="ONLINE").exists()

    return user if permission else None


class RoomListSerializer(serializers.ModelSerializer):
    contact = serializers.CharField(source="contact.name")
    contact_external_id = serializers.CharField(source="contact.external_id")
    waiting_time = serializers.IntegerField(source="metric.waiting_time")
    interaction_time = serializers.IntegerField(source="metric.interaction_time")
    tags = TagSimpleSerializer(many=True, required=False)

    class Meta:
        model = Room
        fields = [
            "uuid",
            "user",
            "contact",
            "contact_external_id",
            "urn",
            "is_active",
            "ended_at",
            "created_on",
            "waiting_time",
            "interaction_time",
            "tags",
        ]


class RoomMetricsSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    first_user_message = serializers.SerializerMethodField()
    tags = TagSimpleSerializer(many=True, required=False)
    interaction_time = serializers.IntegerField(source="metric.interaction_time")
    contact_external_id = serializers.CharField(source="contact.external_id")

    class Meta:
        model = Room
        fields = [
            "created_on",
            "interaction_time",
            "ended_at",
            "contact_external_id",
            "user",
            "user_name",
            "user_assigned_at",
            "first_user_message",
            "tags",
        ]

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return None

    def get_first_user_message(self, obj):
        first_msg = (
            obj.messages.filter(user__isnull=False).order_by("created_on").first()
        )
        if first_msg:
            msg_date = pendulum.instance(first_msg.created_on).in_tz(
                "America/Sao_Paulo"
            )
            return msg_date.isoformat()
        return None


class RoomFlowSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=False, read_only=True)
    user_email = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        required=False,
        source="user",
        slug_field="email",
        write_only=True,
        allow_null=True,
    )
    sector_uuid = serializers.CharField(
        required=False, write_only=True, allow_null=True
    )
    queue_uuid = serializers.PrimaryKeyRelatedField(
        queryset=Queue.objects.all(), required=False, source="queue", write_only=True
    )
    queue = QueueSerializer(many=False, required=False, read_only=True)
    contact = ContactRelationsSerializer(many=False, required=False, read_only=False)
    flow_uuid = serializers.CharField(required=False, write_only=True, allow_null=True)
    is_anon = serializers.BooleanField(write_only=True, required=False, default=False)
    ticket_uuid = serializers.UUIDField(required=False)

    class Meta:
        model = Room
        fields = [
            "uuid",
            "user",
            "queue",
            "ended_at",
            "is_active",
            "transfer_history",
            # Writable Fields
            "sector_uuid",
            "ticket_uuid",
            "queue_uuid",
            "user_email",
            "contact",
            "created_on",
            "custom_fields",
            "callback_url",
            "is_waiting",
            "flow_uuid",
            "urn",
            "is_anon",
            "protocol",
        ]
        read_only_fields = [
            "uuid",
            "user",
            "queue",
            "ended_at",
            "is_active",
            "transfer_history",
        ]
        extra_kwargs = {"queue": {"required": False, "read_only": True}}

    def create(self, validated_data):
        queue, sector = self.get_queue_and_sector(validated_data)
        project = sector.project

        created_on = validated_data.get("created_on", timezone.now().time())
        protocol = validated_data.get("custom_fields", {}).pop("protocol", None)
        service_chat = validated_data.get("custom_fields", {}).pop(
            "service_chats", None
        )

        self.check_work_time(sector, created_on)

        self.handle_urn(validated_data)

        groups, flow_uuid = self.extract_flow_start_data(validated_data)

        contact, created = self.update_or_create_contact(validated_data)

        room = get_active_room_flow_start(contact, flow_uuid, project)

        if room is not None:
            return room

        self.validate_unique_active_project(contact, project)

        user = validated_data.get("user")
        validated_data["user"] = get_room_user(
            contact, queue, user, groups, created, flow_uuid, project
        )

        room = Room.objects.create(
            **validated_data,
            project_uuid=str(queue.project.uuid),
            contact=contact,
            queue=queue,
            protocol=protocol,
            service_chat=service_chat,
        )
        RoomMetrics.objects.create(room=room)

        return room

    def validate_unique_active_project(self, contact, project):
        if Room.objects.filter(
            is_active=True, contact=contact, queue__sector__project=project
        ).exists():
            raise ValidationError(
                {"detail": _("The contact already have an open room in the project")}
            )

    def get_queue_and_sector(self, validated_data):
        try:
            queue = validated_data.pop("queue", None)
            sector = validated_data.pop("sector_uuid", None) or queue.sector
        except AttributeError:
            raise ValidationError(
                {"detail": _("Cannot create a room without queue_uuid or sector_uuid")}
            )

        if queue is None:
            queue = Queue.objects.filter(sector__uuid=sector, is_deleted=False).first()

        sector = queue.sector

        return queue, sector

    def check_work_time(self, sector, created_on):
        if not sector.is_attending(created_on):
            raise ValidationError(
                {"detail": _("Contact cannot be done outside working hours")}
            )
        elif sector.validate_agent_status() is False:
            raise ValidationError(
                {"detail": _("Contact cannot be done when agents are offline")}
            )

    def handle_urn(self, validated_data):
        is_anon = validated_data.pop("is_anon", False)
        urn = validated_data.get("contact", {}).pop("urn", "").split("?")[0]
        if not is_anon:
            validated_data["urn"] = urn

    def extract_flow_start_data(self, validated_data):
        groups = validated_data.get("contact", {}).pop("groups", [])
        flow_uuid = validated_data.pop("flow_uuid", None)
        return groups, flow_uuid

    def update_or_create_contact(self, validated_data):
        contact_data = validated_data.pop("contact")
        contact_external_id = contact_data.pop("external_id")
        return Contact.objects.update_or_create(
            external_id=contact_external_id, defaults=contact_data
        )
