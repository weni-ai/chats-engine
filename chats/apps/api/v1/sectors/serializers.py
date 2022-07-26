from rest_framework import serializers

from chats.apps.sectors.models import Sector, SectorAuthorization, SectorTag

# Sector serializers


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = "__all__"


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


class SectorManagerSerializer(serializers.ModelSerializer):

    name = serializers.CharField(source="user.name")
    email = serializers.CharField(source="user.email")

    class Meta:
        model = SectorAuthorization
        fields = ["name", "email"]


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


class DetailSectorTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorTag
        exclude = [
            "sector",
        ]
