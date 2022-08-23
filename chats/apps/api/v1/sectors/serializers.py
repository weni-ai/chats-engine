from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag

from chats.apps.api.v1.accounts.serializers import UserSerializer


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
                    {
                        "work_end": _(
                            "work_end date must be greater than work_start date."
                        )
                    }
                )
        else:
            if data["work_end"] < data["work_start"]:
                raise serializers.ValidationError(
                    {
                        "work_end": _(
                            "work_end date must be greater than work_start date."
                        )
                    }
                )
        return data

    def validate_rooms_limit(self, data):
        """
        Check if the rooms_limit its greater than 0.
        """
        if data <= 0:
            raise serializers.ValidationError(
                {"you cant create a sector with rooms_limit lower or equal 0."}
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
        ]
        extra_kwargs = {field: {"required": False} for field in fields}


class SectorReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()
    contacts = serializers.SerializerMethodField()

    class Meta:
        model = Sector
        fields = ["uuid", "name", "agents", "contacts"]

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
                    {"name": _("This tag already exists.")}
                )
        else:
            if SectorTag.objects.filter(
                name=data["name"], sector=data["sector"]
            ).exists():
                raise serializers.ValidationError(
                    {"name": _("This tag already exists.")}
                )
        return data


class DetailSectorTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorTag
        exclude = [
            "sector",
        ]
