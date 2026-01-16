from rest_framework import serializers

from chats.apps.accounts.models import User
from chats.apps.api.v1.accounts.serializers import UserNameEmailSerializer
from chats.apps.api.v1.contacts.serializers import ContactSimpleSerializer
from chats.apps.api.v1.sectors.serializers import TagSimpleSerializer
from chats.apps.contacts.models import Contact
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import SectorTag


class ContactOptimizedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["uuid", "name", "external_id"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        room = self.context.get("parent", {}).get("room")

        if room and room.protocol:
            if room.service_chat:
                data["name"] = f"{room.service_chat} | {room.protocol} | {data['name']}"
            else:
                data["name"] = f"{data['name']} | {room.protocol}"

        return data


class RoomHistorySerializer(serializers.ModelSerializer):
    user = UserNameEmailSerializer(many=False, read_only=True)
    contact = ContactOptimizedSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    closed_by = UserNameEmailSerializer(many=False, read_only=True)

    class Meta:
        model = Room
        fields = [
            "uuid",
            "created_on",
            "ended_at",
            "user",
            "contact",
            "tags",
            "protocol",
            "service_chat",
            "closed_by",
        ]

    def get_tags(self, obj):
        return TagSimpleSerializer(
            # Including the (soft) deleted tags
            SectorTag.all_objects.filter(rooms__in=[obj]),
            many=True,
        ).data

    def get_closed_by(self, obj):
        if not obj.ended_by:
            return None
        try:
            user = User.objects.get(email=obj.ended_by)
            return {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
            }
        except User.DoesNotExist:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        contact_serializer = ContactOptimizedSerializer(
            instance.contact, context={"parent": {"room": instance}}
        )
        data["contact"] = contact_serializer.data

        return data


class RoomBasicValuesSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    ended_at = serializers.DateTimeField()


class RoomDetailSerializer(serializers.ModelSerializer):
    user = UserNameEmailSerializer(many=False, read_only=True)
    contact = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "uuid",
            "custom_fields",
            "urn",
            "created_on",
            "ended_at",
            "user",
            "contact",
            "tags",
            "protocol",
        ]

    def get_contact(self, obj):
        contact_data = ContactSimpleSerializer(obj.contact).data
        if obj.protocol:
            contact_data["name"] = f"{contact_data['name']} | {obj.protocol}"
        return contact_data

    def get_tags(self, obj):
        return TagSimpleSerializer(
            # Including the (soft) deleted tags
            SectorTag.all_objects.filter(rooms__in=[obj]),
            many=True,
        ).data
