from rest_framework import serializers

from chats.apps.api.v1.sectors.serializers import SectorSerializer
from chats.apps.sectors.models import GroupSector, GroupSectorAuthorization


class GroupSectorSerializer(serializers.ModelSerializer):
    sectors = serializers.SerializerMethodField()

    class Meta:
        model = GroupSector
        fields = [
            "uuid",
            "name",
            "project",
            "rooms_limit",
            "sectors",
        ]

    def get_sectors(self, obj):
        return SectorSerializer(obj.sectors.all(), many=True).data


class GroupSectorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupSector
        fields = [
            "uuid",
            "name",
        ]


class GroupSectorUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupSector
        fields = ["name", "rooms_limit"]
        read_only_fields = ["project"]

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.rooms_limit = validated_data.get("rooms_limit", instance.rooms_limit)
        instance.save()
        return instance


class GroupSectorAuthorizationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = GroupSectorAuthorization
        fields = [
            "uuid",
            "group_sector",
            "permission",
            "role",
            "user_name",
            "user_email",
        ]
        read_only_fields = ["uuid"]

    def validate(self, attrs):
        if attrs.get("role") not in [
            GroupSectorAuthorization.ROLE_MANAGER,
            GroupSectorAuthorization.ROLE_AGENT,
        ]:
            raise serializers.ValidationError(
                {"role": "Invalid role. Must be 1 (manager) or 2 (agent)"}
            )
        return attrs

    def get_user_name(self, obj):
        return obj.permission.user.full_name

    def get_user_email(self, obj):
        return obj.permission.user.email
