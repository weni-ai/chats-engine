from rest_framework import serializers

from chats.apps.api.utils import calculate_in_service_time


class InternalDashboardQueryParamsSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    agent = serializers.CharField(required=False)
    sector = serializers.ListField(child=serializers.CharField(), required=False)
    tag = serializers.ListField(child=serializers.CharField(), required=False)
    queue = serializers.ListField(child=serializers.CharField(), required=False)
    user_request = serializers.CharField(required=False)
    is_weni_admin = serializers.BooleanField(required=False)
    ordering = serializers.CharField(required=False)
    status = serializers.ListField(child=serializers.CharField(), required=False)
    custom_status = serializers.ListField(child=serializers.CharField(), required=False)


class DashboardAgentsSerializerV2(serializers.Serializer):
    link = serializers.SerializerMethodField()
    opened = serializers.IntegerField(allow_null=True, required=False)
    agent = serializers.SerializerMethodField()
    closed = serializers.IntegerField(allow_null=True, required=False)
    status = serializers.SerializerMethodField()
    avg_first_response_time = serializers.IntegerField(allow_null=True, required=False)
    avg_message_response_time = serializers.IntegerField(
        allow_null=True, required=False
    )
    avg_interaction_time = serializers.IntegerField(allow_null=True, required=False)
    time_in_service = serializers.SerializerMethodField()

    def get_link(self, obj):
        return {
            "url": f"chats:dashboard/view-mode/{obj.get('email', '')}",
            "type": "internal",
        }

    def get_status(self, obj):
        custom_status_list = obj.get("custom_status") or []

        if custom_status_list:
            for status_item in custom_status_list:
                status_type = status_item.get("status_type")
                is_active = status_item.get("is_active", False)

                if status_type != "In-Service" and is_active:
                    return {"status": "custom", "label": status_type}

        if obj.get("status") == "ONLINE":
            return {"status": "online", "label": None}
        elif obj.get("status") == "OFFLINE":
            return {"status": "offline", "label": None}

        return {"status": "offline", "label": None}

    def get_agent(self, obj):
        name = f"{obj.get('first_name')} {obj.get('last_name')}"

        return {
            "name": name,
            "email": obj.get("email"),
            "is_deleted": obj.get("is_deleted", False),
        }

    def get_time_in_service(self, obj):
        return calculate_in_service_time(
            obj.get("custom_status"), user_status=obj.get("status")
        )
