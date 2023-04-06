from rest_framework import serializers

from chats.apps.sectors.models import SectorTag


class SectorTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorTag
        fields = "__all__"
