from rest_framework import serializers


class DashboardAgentsSerializer(serializers.Serializer):
    link = serializers.SerializerMethodField()
    opened = serializers.SerializerMethodField()
    closed = serializers.SerializerMethodField()
    agent = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_link(self, obj):
        return {
            "url": f"chats:dashboard/view-mode/{obj.get('email', '')}",
            "type": "internal",
        }

    def get_status(self, obj):
        if obj.get("status") == "ONLINE":
            return "green"
        return "gray"

    def get_agent(self, obj):
        return f"{obj.get('first_name')} {obj.get('last_name')}"

    def get_opened(self, obj):
        return obj.get("opened")

    def get_closed(self, obj):
        return obj.get("closed")
