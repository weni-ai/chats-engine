import logging
from typing import Dict, List

import pendulum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from sentry_sdk import capture_exception

from chats.apps.accounts.models import User
from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactRelationsSerializer
from chats.apps.api.v1.queues.serializers import QueueSerializer
from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.queues.utils import start_queue_priority_routing
from chats.apps.rooms.models import Room
from chats.apps.rooms.views import close_room
from chats.apps.sectors.models import Sector

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

    # General room routing type
    return queue.get_available_agent()


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
    history = serializers.ListField(
        child=serializers.DictField(), required=False, write_only=True
    )
    project_info = ProjectInfoSerializer(required=False, write_only=True)

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
        attrs["config"] = self.initial_data.get("project_info", {})

        if "project_info" in attrs:
            attrs.pop("project_info")

        sector_uuid = attrs.get("sector_uuid")

        working_hours_config = {}
        if sector_uuid:
            try:
                sector = Sector.objects.get(uuid=sector_uuid)
                working_hours_config = (
                    sector.working_day.get("working_hours", {})
                    if sector.working_day
                    else {}
                )

                if not working_hours_config:
                    return attrs

                logger.info("flows json config to open a room: %s", attrs)
                created_on = self.initial_data.get("created_on", timezone.now())
                if isinstance(created_on, str):
                    created_on = pendulum.parse(created_on)
                else:
                    created_on = pendulum.instance(created_on)

                project_tz = pendulum.timezone(str(sector.project.timezone))
                if created_on.tzinfo is None:
                    created_on = project_tz.localize(created_on)
                else:
                    created_on = created_on.in_timezone(project_tz)

                attrs["created_on"] = created_on

                if working_hours_config:
                    self.check_work_time_weekend(sector, created_on)

            except serializers.ValidationError as error:
                raise error
            except Exception as error:
                capture_exception(error)
                logger.error("Error getting sector: %s", error)

        return attrs

    def create(self, validated_data):
        history_data = validated_data.pop("history", [])

        queue, sector = self.get_queue_and_sector(validated_data)
        project = sector.project

        created_on = validated_data.get("created_on", timezone.now())

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

    def check_work_time_weekend(self, sector, created_on):
        working_hours_config = (
            sector.working_day.get("working_hours", {}) if sector.working_day else {}
        )

        if not working_hours_config:
            return

        weekday = created_on.isoweekday()

        if weekday in (6, 7):
            if not working_hours_config.get("open_in_weekends", False):
                raise ValidationError(
                    {"detail": _("Contact cannot be done outside working hours")}
                )

            schedules = working_hours_config.get("schedules", {})
            day_key = "saturday" if weekday == 6 else "sunday"
            day_range = schedules.get(day_key, {})
            current_time = created_on.time()

            start_time_str = day_range.get("start")
            end_time_str = day_range.get("end")

            if start_time_str is None or end_time_str is None:
                logger.info(
                    "there is a try to create a room out of working hours range %s",
                    created_on,
                )
                raise ValidationError(
                    {"detail": _("Contact cannot be done outside working hours")}
                )

            start_time = pendulum.parse(start_time_str).time()
            end_time = pendulum.parse(end_time_str).time()

            if not (start_time <= current_time <= end_time):
                logger.info(
                    "there is a try to create a room out of working hours %s",
                    created_on,
                )
                raise ValidationError(
                    {"detail": _("Contact cannot be done outside working hours")}
                )

            logger.info("an room its created in the weekend %s", created_on)

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
            created_messages = Message.objects.bulk_create(messages_to_create)

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
