from rest_framework import serializers

from chats.apps.sectors.models import Sector


class SectorFlowSerializer(serializers.ModelSerializer):
    """
    Serializer for sector data via external API.

    Returns the sector UUID and name.
    """

    class Meta:
        model = Sector
        fields = [
            "uuid",
            "name",
        ]
        extra_kwargs = {
            "uuid": {"help_text": "Unique identifier of the sector"},
            "name": {"help_text": "Display name of the sector"},
        }
