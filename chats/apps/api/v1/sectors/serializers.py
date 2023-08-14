from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag

User = get_user_model()


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = "__all__"

    def validate(self, data):
        """
        Check if the work_end date its greater than work_start date.
        """
        if self.instance:
            if self.instance.work_end < self.instance.work_start:
                raise serializers.ValidationError(
                    {"detail": _("work_end date must be greater than work_start date.")}
                )
        else:
            if data["work_end"] < data["work_start"]:
                raise serializers.ValidationError(
                    {"detail": _("work_end date must be greater than work_start date.")}
                )
        return data


class SectorUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = [
            "name",
            "rooms_limit",
            "work_start",
            "work_end",
            "is_deleted",
            "can_trigger_flows",
            "sign_messages",
            "can_edit_custom_fields",
            "config",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}

    def update(self, instance, validated_data):
        config = validated_data.pop("config", None)
        sector = super().update(instance, validated_data)
        if config:
            sector.config = sector.config or {}
            sector.config.update(config)
            sector.save()
        return sector


class SectorReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()
    contacts = serializers.SerializerMethodField()

    class Meta:
        model = Sector
        fields = [
            "uuid",
            "name",
            "agents",
            "contacts",
            "can_trigger_flows",
            "created_on",
        ]

    def get_agents(self, sector: Sector):
        return sector.agent_count

    def get_contacts(self, sector: Sector):
        return sector.contact_count


class SectorReadOnlyRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = [
            "uuid",
            "name",
            "work_start",
            "work_end",
            "rooms_limit",
            "can_trigger_flows",
            "sign_messages",
            "can_edit_custom_fields",
        ]


class SectorWSSerializer(serializers.ModelSerializer):
    """
    used to serialize data for the websocket connection
    TODO: Add a field checking if the sector can receive new rooms based on work_start and work_end
    """

    class Meta:
        model = Sector
        fields = "__all__"


# Sector Authorization Serializers


class SectorAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorAuthorization
        fields = "__all__"


class SectorAuthorizationReadOnlySerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = SectorAuthorization
        fields = [
            "uuid",
            "sector",
            "role",
            "user",
        ]

    def get_user(self, auth):
        return UserSerializer(auth.permission.user).data


class SectorAuthorizationWSSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorAuthorization
        fields = "__all__"


# Sector Tags Serializer


class SectorTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorTag
        fields = "__all__"
        extra_kwargs = {"sector": {"required": False}}

    def validate(self, data):
        """
        Check if tag already exist in sector.
        """
        if self.instance:
            if SectorTag.objects.filter(
                sector=self.instance.sector, name=data["name"]
            ).exists():
                raise serializers.ValidationError(
                    {"detail": _("This tag already exists.")}
                )
        else:
            if SectorTag.objects.filter(
                name=data["name"], sector=data["sector"]
            ).exists():
                raise serializers.ValidationError(
                    {"detail": _("This tag already exists.")}
                )
        return data


class DetailSectorTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorTag
        exclude = [
            "sector",
        ]


class SectorAgentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "photo_url",
            "language",
        ]
