from rest_framework import serializers


class DashboardAgentsSerializer(serializers.Serializer):
    link = serializers.SerializerMethodField()
    opened = serializers.IntegerField(allow_null=True, required=False)
    agent = serializers.SerializerMethodField()
    closed = serializers.IntegerField(allow_null=True, required=False)
    status = serializers.SerializerMethodField()
    custom_status = serializers.SerializerMethodField()

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

    def get_custom_status(self, obj):
        custom_status_list = obj.get("custom_status")

        if not custom_status_list:
            return None

        aggregated_status = {}

        for status_item in custom_status_list:
            status_type = status_item.get("status_type")
            break_time = status_item.get("break_time", 0)

            if status_type in aggregated_status:
                aggregated_status[status_type] += break_time
            else:
                aggregated_status[status_type] = break_time

        aggregated_status_list = [
            {"status_type": status_type, "break_time": total_time}
            for status_type, total_time in aggregated_status.items()
        ]

        return aggregated_status_list
