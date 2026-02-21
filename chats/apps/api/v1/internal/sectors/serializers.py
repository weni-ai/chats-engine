from rest_framework import serializers

from chats.apps.sectors.models import Sector, SectorTag


class SectorTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorTag
        fields = "__all__"


class SectorRequiredTagsSerializer(serializers.ModelSerializer):
    """Serializer to check if a sector has required_tags enabled."""

    class Meta:
        model = Sector
        fields = ["uuid", "required_tags"]
        read_only_fields = ["uuid", "required_tags"]
