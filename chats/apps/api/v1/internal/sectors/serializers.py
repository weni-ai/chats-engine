from chats.apps.sectors.models import SectorTag
from chats.core.serializers import AuditableModelSerializer


class SectorTagSerializer(AuditableModelSerializer):
    class Meta:
        model = SectorTag
        fields = "__all__"

    def _get_audit_project(self):
        if self.instance is not None:
            return self.instance.sector.project
        sector = (self.validated_data or {}).get("sector")
        return sector.project if sector else None
