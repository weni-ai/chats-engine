from chats.apps.quickmessages.models import QuickMessage
from chats.core.serializers import AuditableModelSerializer


class QuickMessageSerializer(AuditableModelSerializer):
    class Meta:
        model = QuickMessage
        fields = "__all__"
        read_only_fields = ("user",)

    def _get_audit_project(self):
        if self.instance is not None:
            return self.instance.sector.project if self.instance.sector else None
        sector = (self.validated_data or {}).get("sector")
        return sector.project if sector else None
