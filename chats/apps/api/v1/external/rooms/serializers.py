from typing import Dict, List

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from chats.apps.accounts.models import User
from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.api.v1.contacts.serializers import ContactRelationsSerializer
from chats.apps.api.v1.queues.serializers import QueueSerializer
from chats.apps.contacts.models import Contact
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room


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
        is_anon = validated_data.pop("is_anon")
        try:
            queue = (
                None if not validated_data.get("queue") else validated_data.pop("queue")
            )
            sector = (
                queue.sector
                if not validated_data.get("sector_uuid")
                else validated_data.pop("sector_uuid")
            )
        except AttributeError:
            raise ValidationError(
                {"detail": _("Cannot create room without queue_uuid or sector_uuid")}
            )

        if queue is None and sector is not None:
            queue = Queue.objects.filter(sector__uuid=sector, is_deleted=False).first()

        sector = queue.sector

        created_on = validated_data.get("created_on", timezone.now().time())
        if sector.is_attending(created_on) is False:
            raise ValidationError(
                {"detail": _("Contact cannot be done outside working hours")}
            )

        contact_data = validated_data.pop("contact")
        contact_external_id = contact_data.pop("external_id")

        project = sector.project
        user = validated_data.get("user")
        groups = []
        flow_uuid = None
        if contact_data.get("groups"):
            groups = contact_data.pop("groups")

        if validated_data.get("flow_uuid"):
            flow_uuid = validated_data.pop("flow_uuid")

        if contact_data.get("urn"):
            urn = contact_data.pop("urn").split("?")[0]
            if not is_anon:
                validated_data["urn"] = urn
        contact, created = Contact.objects.update_or_create(
            external_id=contact_external_id, defaults=contact_data
        )

        room = get_active_room_flow_start(contact, flow_uuid, project)
        if room is not None:
            return room
        validated_data["user"] = get_room_user(
            contact, queue, user, groups, created, flow_uuid, project
        )

        room = Room.objects.create(**validated_data, contact=contact, queue=queue)
        RoomMetrics.objects.create(room=room)

        return room
