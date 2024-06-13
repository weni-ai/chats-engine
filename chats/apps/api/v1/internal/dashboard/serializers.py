from rest_framework import serializers


class DashboardAgentsSerializer(serializers.Serializer):
    link = serializers.SerializerMethodField()
    opened = serializers.IntegerField(allow_null=True, required=False)
    agent = serializers.SerializerMethodField()
    closed = serializers.IntegerField(allow_null=True, required=False)
    status = serializers.SerializerMethodField()

    def get_link(self, obj):
        return {
            "url": f"chats:dashboard/view-mode/:{obj.get('email', '')}",
            "type": "internal",
        }

    def get_status(self, obj):
        if obj.get("status") == "ONLINE":
            return "green"
        return "gray"

    def get_agent(self, obj):
        return f"{obj.get('first_name')} {obj.get('last_name')}"
