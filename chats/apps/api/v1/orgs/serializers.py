from rest_framework import serializers

from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector


class OrgProjectSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    its_principal = serializers.SerializerMethodField()
    has_sector_integration = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["uuid", "its_principal", "name", "has_sector_integration"]

    def get_its_principal(self, obj):
        try:
            return obj.config.get("its_principal", False)
        except AttributeError:
            return None

    def get_has_sector_integration(self, obj):
        return Sector.objects.filter(config__secondary_project=str(obj.uuid)).exists()
