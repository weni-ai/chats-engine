import logging
from typing import Dict, List, Optional

import pendulum
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from weni.feature_flags.shortcuts import is_feature_active

from chats.apps.accounts.models import User
from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactRelationsSerializer
from chats.apps.api.v1.queues.serializers import QueueSerializer
from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.msgs.models import AutomaticMessage, Message, MessageMedia
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.queues.utils import start_queue_priority_routing
from chats.apps.rooms.models import Room
from chats.apps.rooms.views import close_room
from chats.apps.sectors.utils import working_hours_validator


logger = logging.getLogger(__name__)


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
    project: Project,
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

    if user and project.permissions.filter(user=user, status="ONLINE").exists():
        return user

    if project.use_queue_priority_routing:
        current_queue_size = queue.rooms.filter(
            is_active=True, user__isnull=True
        ).count()

        if current_queue_size == 0:
            # If the queue is empty, the available user with the least number
            # of rooms will be selected, if any.
            return queue.get_available_agent()

        logger.info(
            "Calling start_queue_priority_routing for queue %s from get_room_user because the queue is not empty",
            queue.uuid,
        )
        start_queue_priority_routing(queue)

        # If the queue is not empty, the room must stay in the queue,
        # so that, when a agent becomes available, the first room in the queue
        # will be assigned to the them. This logic is not done here.
        return None

    if queue.rooms.filter(is_active=True, user__isnull=True).exists():
        return None

    # General room routing type
    return queue.get_available_agent()


class RoomListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing rooms via external API.

    Returns room details including contact info, agent, metrics and tags.
    """

    contact = serializers.CharField(
        source="contact.name",
        help_text="Contact display name",
    )
    contact_external_id = serializers.CharField(
        source="contact.external_id",
        help_text="Contact external ID from the source system",
    )
    waiting_time = serializers.IntegerField(
        source="metric.waiting_time",
        help_text="Time in seconds the room waited in queue",
    )
    interaction_time = serializers.IntegerField(
        source="metric.interaction_time",
        help_text="Total interaction time in seconds",
    )
    tags = TagSimpleSerializer(
        many=True,
        required=False,
        help_text="List of tags associated with the room",
    )

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
    """
    Serializer for room metrics via external API.

    Returns detailed metrics including interaction time, tags, protocol,
    automatic message timing, and custom fields.
    """

    user_name = serializers.SerializerMethodField(
        help_text="Full name of the assigned agent",
    )
    first_user_message = serializers.SerializerMethodField(
        help_text="Timestamp of the first agent message (ISO 8601)",
    )
    tags = TagSimpleSerializer(
        many=True,
        required=False,
        help_text="List of tags associated with the room",
    )
    interaction_time = serializers.IntegerField(
        source="metric.interaction_time",
        help_text="Total interaction time in seconds",
    )
    urn = serializers.CharField(
        help_text="Contact URN (e.g., whatsapp:5511999999999)",
    )
    contact_external_id = serializers.CharField(
        source="contact.external_id",
        help_text="Contact external ID from the source system",
    )
    protocol = serializers.CharField(
        read_only=True,
        help_text="Room protocol number",
    )
    callid = serializers.SerializerMethodField(
        help_text="Call ID from custom fields (if available)",
    )
    automatic_message_sent_at = serializers.SerializerMethodField(
        help_text="Timestamp when automatic message was sent (ISO 8601)",
    )
    first_user_assigned_at = serializers.DateTimeField(
        help_text="Timestamp when first agent was assigned (ISO 8601)",
    )
    time_to_send_automatic_message = serializers.SerializerMethodField(
        help_text="Time in seconds from assignment to automatic message",
    )
    sector = serializers.SerializerMethodField(
        help_text="Sector info: {uuid, name}",
    )
    custom_fields = serializers.JSONField(
        read_only=True,
        help_text="Custom fields as JSON object",
    )

    class Meta:
        model = Room
        fields = [
            "created_on",
            "interaction_time",
            "ended_at",
            "urn",
            "contact_external_id",
            "user",
            "user_name",
            "user_assigned_at",
            "first_user_message",
            "tags",
            "protocol",
            "callid",
            "automatic_message_sent_at",
            "first_user_assigned_at",
            "time_to_send_automatic_message",
            "sector",
            "custom_fields",
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

    def get_callid(self, obj: Room) -> Optional[str]:
        custom_fields = obj.custom_fields or {}

        return custom_fields.get("callid", None)

    def get_automatic_message_sent_at(self, obj: Room) -> Optional[str]:
        automatic_message: AutomaticMessage = AutomaticMessage.objects.filter(
            room=obj
        ).first()

        if automatic_message:
            msg_date = pendulum.instance(automatic_message.message.created_on).in_tz(
                "America/Sao_Paulo"
            )
            return msg_date.isoformat()

        return None

    def get_time_to_send_automatic_message(self, obj: Room) -> Optional[str]:
        automatic_message: AutomaticMessage = AutomaticMessage.objects.filter(
            room=obj
        ).first()

        if automatic_message and obj.first_user_assigned_at:
            return max(
                int(
                    (
                        automatic_message.message.created_on
                        - obj.first_user_assigned_at
                    ).total_seconds()
                ),
                0,
            )

        return None

    def get_sector(self, obj: Room) -> Optional[dict]:
        sector = obj.queue.sector if obj.queue else None

        if sector:
            return {
                "uuid": sector.uuid,
                "name": sector.name,
            }

        return None


class ProjectInfoSerializer(serializers.Serializer):
    """
    Serializer for representing basic project information.

    Used for including minimal project details in other serializers,
    particularly in the context of room flow operations.

    Fields:
        uuid: The unique identifier of the project
        name: The display name of the project
    """

    uuid = serializers.UUIDField(required=False, read_only=False)
    name = serializers.CharField(required=False, read_only=False)


class RoomFlowSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and managing rooms (tickets) via external API.

    Supports room creation with queue or sector assignment, contact data,
    optional flow start, and message history.
    """

    user = UserSerializer(many=False, required=False, read_only=True)
    user_email = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        required=False,
        source="user",
        slug_field="email",
        write_only=True,
        allow_null=True,
        help_text="Email of the agent to assign to the room",
    )
    sector_uuid = serializers.CharField(
        required=False,
        write_only=True,
        allow_null=True,
        help_text="UUID of the sector (alternative to queue_uuid)",
    )
    queue_uuid = serializers.PrimaryKeyRelatedField(
        queryset=Queue.objects.all(),
        required=False,
        source="queue",
        write_only=True,
        help_text="UUID of the queue to assign the room",
    )
    queue = QueueSerializer(many=False, required=False, read_only=True)
    contact = ContactRelationsSerializer(
        many=False,
        required=False,
        read_only=False,
        help_text="Contact data (external_id, name, email, phone, custom_fields)",
    )
    flow_uuid = serializers.CharField(
        required=False,
        write_only=True,
        allow_null=True,
        help_text="UUID of the flow that started this room",
    )
    is_anon = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
        help_text="If true, the URN will not be saved",
    )
    ticket_uuid = serializers.UUIDField(
        required=False,
        help_text="External ticket UUID for integration",
    )
    history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True,
        help_text="List of messages to create as history",
    )
    project_info = ProjectInfoSerializer(
        required=False,
        write_only=True,
        help_text="Project information for context",
    )

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
            "history",
            "project_info",
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

    def validate(self, attrs):
        # Mantém somente limpeza de project_info; validação de horário ocorre em create()
        attrs["config"] = self.initial_data.get("project_info", {})
        if "project_info" in attrs:
            attrs.pop("project_info")
        return attrs

    def create(self, validated_data):
        history_data = validated_data.pop("history", [])

        queue, sector = self.get_queue_and_sector(validated_data)
        project = sector.project

        created_on = self.initial_data.get(
            "created_on", validated_data.get("created_on", timezone.now())
        )

        protocol = validated_data.pop("protocol", None)

        if protocol in (None, ""):
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
            update_fields = []

            if "callback_url" in self.initial_data:
                new_callback_url = validated_data.get("callback_url")
                if new_callback_url is not None:
                    room.callback_url = new_callback_url
                    update_fields.append("callback_url")

            if "ticket_uuid" in self.initial_data:
                new_ticket_uuid = validated_data.get("ticket_uuid")
                if new_ticket_uuid is not None:
                    room.ticket_uuid = new_ticket_uuid
                    update_fields.append("ticket_uuid")

            if update_fields:
                room.request_callback(room.serialized_ws_data)
                room.save(update_fields=update_fields)

            if history_data:
                self.process_message_history(room, history_data)
            return room

        room = self.validate_unique_active_project(contact, project)

        if room is not None:
            return room

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

        if history_data:
            self.process_message_history(room, history_data)
        return room

    def validate_unique_active_project(self, contact, project):
        queryset = Room.objects.filter(
            is_active=True, contact=contact, queue__sector__project=project
        )

        if queryset.exists():
            config = project.config or {}

            if config.get("ignore_close_rooms_on_flow_start", False):
                room = queryset.first()
                room.request_callback(room.serialized_ws_data)

                room.callback_url = self.validated_data.get("callback_url")
                room.ticket_uuid = self.validated_data.get("ticket_uuid")
                room.save(update_fields=["callback_url", "ticket_uuid"])

                return room

            raise ValidationError(
                {"detail": _("The contact already have an open room in the project")}
            )

    def get_queue_and_sector(self, validated_data):
        """
        Resolve sempre a queue e usa seu setor; se sector_uuid também vier, garante consistência.
        """
        queue = validated_data.pop(
            "queue", None
        )  # já vem instanciada pelo PrimaryKeyRelatedField
        provided_sector_uuid = validated_data.pop("sector_uuid", None)

        if queue is None and provided_sector_uuid is None:
            raise ValidationError(
                {"detail": _("Cannot create a room without queue_uuid or sector_uuid")}
            )

        if queue is None:
            queue = Queue.objects.filter(
                sector__uuid=provided_sector_uuid, is_deleted=False
            ).first()
            if queue is None:
                raise ValidationError(
                    {"detail": _("No active queue found for provided sector_uuid")}
                )

        sector = queue.sector
        if provided_sector_uuid and str(provided_sector_uuid) != str(sector.uuid):
            raise ValidationError(
                {"detail": _("queue_uuid does not belong to provided sector_uuid")}
            )

        is_limit_active_for_queue = queue.queue_limit_info.is_active

        if is_limit_active_for_queue:
            # Only check if the feature flag is enabled and make all the other validations
            # if the queue limit for this particular queue is active
            is_queue_limit_feature_active = is_feature_active(
                settings.QUEUE_LIMIT_FEATURE_FLAG_KEY,
                None,
                str(sector.project.uuid),
            )
            queue_limit = (
                queue.queue_limit_info.limit
                if not isinstance(queue.queue_limit_info.limit, int)
                else 0
            )

            if (
                is_queue_limit_feature_active
                and queue.queued_rooms_count >= queue_limit
            ):
                raise ValidationError(
                    {"error": "human_support_queue_limit_reached"},
                    code="human_support_queue_limit_reached",
                )

        return queue, sector

    def check_work_time(self, sector, created_on):
        """
        Validate using sector.working_day['working_hours'] exclusively.
        """
        if isinstance(created_on, str):
            created_on_dt = pendulum.parse(created_on)
        else:
            created_on_dt = pendulum.instance(created_on)

        project_tz = pendulum.timezone(str(sector.project.timezone))
        created_on_dt = (
            project_tz.localize(created_on_dt)
            if created_on_dt.tzinfo is None
            else created_on_dt.in_timezone(project_tz)
        )

        # Working hours validation (raises ValidationError when blocked)
        try:
            working_hours_validator.validate_working_hours(sector, created_on_dt)
        except ValidationError as e:
            raise serializers.ValidationError({"detail": e.detail})

        # Agent status validation unchanged
        if sector.validate_agent_status() is False:
            raise ValidationError(
                {"detail": _("Contact cannot be done when agents are offline")}
            )

    def check_work_time_weekend(self, sector, created_on):
        """
        Verify if the sector allows room opening at the specified time.
        Uses the WorkingHoursValidator utility for optimized validation.
        """
        working_hours_validator.validate_working_hours(sector, created_on)

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

    def process_message_history(self, room, messages_data):
        is_waiting = room.get_is_waiting()
        was_24h_valid = room.is_24h_valid
        need_update_room = False
        any_incoming_msgs = False

        messages_to_create = []
        media_data_map = {}

        for message_index, msg_data in enumerate(messages_data):
            direction = msg_data.pop("direction")
            medias = msg_data.pop("attachments", [])
            text = msg_data.get("text")
            created_on = msg_data.get("created_on")

            if text is None and not medias:
                raise serializers.ValidationError(
                    {"detail": "Cannot create message without text or media"}
                )

            if direction == "incoming":
                msg_data["contact"] = room.contact
                any_incoming_msgs = True

                if is_waiting:
                    need_update_room = True
                    room.is_waiting = False
                elif not was_24h_valid:
                    need_update_room = True

            msg_data["room"] = room
            msg_data["created_on"] = created_on
            message = Message(**msg_data)
            messages_to_create.append(message)

            if medias:
                media_data_map[message_index] = medias

        if need_update_room:
            room.save()

        if messages_to_create:
            created_messages: list[Message] = Message.objects.bulk_create(
                messages_to_create
            )

            all_media = []
            for message_index, message in enumerate(created_messages):
                if message_index in media_data_map:
                    for media_data in media_data_map[message_index]:
                        all_media.append(
                            MessageMedia(
                                content_type=media_data["content_type"],
                                media_url=media_data["url"],
                                message=message,
                            )
                        )

            if all_media:
                MessageMedia.objects.bulk_create(all_media)

            room.notify_room("create")

            if room.user is None and room.contact and any_incoming_msgs:
                room.trigger_default_message()

            last_msg = created_messages[-1]
            room.on_new_message(
                message=last_msg,
                contact=last_msg.contact,
                increment_unread=len(created_messages),
            )
