from django.db.models import Q

from rest_framework import serializers

from chats.apps.api.utils import calculate_in_service_time
from chats.apps.projects.models.models import CustomStatusType


class InternalDashboardQueryParamsSerializer(serializers.Serializer):
    start_date = serializers.CharField(required=False)
    end_date = serializers.CharField(required=False)
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


class DashboardCustomStatusByAgentSerializerV2(serializers.Serializer):
    agent = serializers.SerializerMethodField()
    custom_status = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()

    def get_agent(self, obj):
        name = f"{obj.first_name} {obj.last_name}"

        return {
            "name": name,
            "email": obj.email,
            "is_deleted": getattr(obj, "is_deleted", False),
        }

    def get_custom_status(self, obj):
        project = self.context.get("project")
        custom_status_types = CustomStatusType.objects.filter(
            Q(project=project) & Q(is_deleted=False) & ~Q(name__iexact="In-Service")
        ).values_list("name", flat=True)

        custom_status_list = getattr(obj, "custom_status", []) or []

        status_dict = {status_type: 0 for status_type in custom_status_types}

        for status_item in custom_status_list:
            status_type = status_item.get("status_type")
            break_time = status_item.get("break_time", 0)

            if status_type in status_dict:
                status_dict[status_type] += break_time
            else:
                status_dict[status_type] = break_time

        return [
            {"status_type": status_type, "break_time": break_time}
            for status_type, break_time in status_dict.items()
        ]

    def get_link(self, obj):
        return {
            "url": f"chats:dashboard/view-mode/{obj.email}",
            "type": "internal",
        }
