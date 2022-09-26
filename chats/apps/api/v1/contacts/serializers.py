from rest_framework import serializers

from chats.apps.contacts.models import Contact


class ContactSerializer(serializers.ModelSerializer):

    room = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            "uuid",
            "name",
            "email",
            "status",
            "custom_fields",
            "room",
            "created_on",
        ]
        read_only_fields = [
            "uuid",
        ]

    def get_room(self, contact: Contact):
        # TODO: Needs refactoring, used to fix circular import as rooms serializers uses contact serializers
        from chats.apps.api.v1.rooms.serializers import RoomContactSerializer

        try:
            return RoomContactSerializer(
                contact.last_room(self.context.get("request")), many=False
            ).data
        except AttributeError:
            return None


class ContactRelationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "uuid",
            "external_id",
            "name",
            "email",
            "status",
            "phone",
            "custom_fields",
            "created_on",
        ]
        read_only_fields = [
            "uuid",
        ]


class ContactWSSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"
