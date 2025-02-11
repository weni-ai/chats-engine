from rest_framework import serializers
from chats.apps.api.v1.sectors.serializers import SectorSerializer
from chats.apps.sectors.models import GroupSector
from chats.apps.sectors.models import GroupSectorAuthorization


class GroupSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupSector
        fields = [
            "name",
            "project",
            "rooms_limit",
        ]


class GroupSectorListSerializer(serializers.ModelSerializer):
    sectors = SectorSerializer(many=True, read_only=True)

    class Meta:
        model = GroupSector
        fields = "__all__"


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
    class Meta:
        model = GroupSectorAuthorization
        fields = ["group_sector", "permission", "role"]
        read_only_fields = ["group_sector"]

    def validate(self, attrs):
        if attrs.get("role") not in [GroupSectorAuthorization.ROLE_MANAGER, GroupSectorAuthorization.ROLE_AGENT]:
            raise serializers.ValidationError({"role": "Invalid role. Must be 1 (manager) or 2 (agent)"})
        return attrs
