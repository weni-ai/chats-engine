from rest_framework import serializers

from chats.apps.api.utils import calculate_in_service_time


class DashboardAgentsSerializer(serializers.Serializer):
    link = serializers.SerializerMethodField()
    opened = serializers.IntegerField(allow_null=True, required=False)
    agent = serializers.SerializerMethodField()
    agent_email = serializers.EmailField(
        source="email", allow_null=True, required=False
    )
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
        return f"{obj.get('first_name')} {obj.get('last_name')}"

    def get_time_in_service(self, obj):
        return calculate_in_service_time(
            obj.get("custom_status"), user_status=obj.get("status")
        )


class DashboardCustomAgentStatusSerializer(serializers.Serializer):
    link = serializers.SerializerMethodField()
    opened = serializers.IntegerField(allow_null=True, required=False)
    agent = serializers.SerializerMethodField()
    agent_email = serializers.EmailField(
        source="email", allow_null=True, required=False
    )
    closed = serializers.IntegerField(allow_null=True, required=False)
    status = serializers.SerializerMethodField()
    custom_status = serializers.SerializerMethodField()
    in_service_time = serializers.SerializerMethodField()
    agent_email = serializers.EmailField(
        source="email", allow_null=True, required=False
    )

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
        return f"{obj.get('first_name')} {obj.get('last_name')}"

    def get_custom_status(self, obj):
        custom_status_list = obj.get("custom_status") or []
        user_status = obj.get("status")

        in_service_time = calculate_in_service_time(custom_status_list, user_status)

        project = self.context.get("project")
        all_status_types = project.custom_statuses.filter(is_deleted=False).values_list(
            "name", flat=True
        )

        status_dict = {status_type: 0 for status_type in all_status_types}

        if custom_status_list:
            for status_item in custom_status_list:
                status_type = status_item.get("status_type")
                break_time = status_item.get("break_time", 0)
                if status_type in status_dict and status_type != "In-Service":
                    status_dict[status_type] += break_time

        if "In-Service" in status_dict:
            status_dict["In-Service"] = in_service_time

        result = [
            {"status_type": status_type, "break_time": break_time}
            for status_type, break_time in status_dict.items()
        ]

        return result

    def get_in_service_time(self, obj):
        return calculate_in_service_time(
            obj.get("custom_status"), user_status=obj.get("status")
        )


class DashboardCSATScoreGeneralSerializer(serializers.Serializer):
    rooms = serializers.IntegerField()
    reviews = serializers.IntegerField()
    avg_rating = serializers.DecimalField(
        allow_null=True, max_digits=3, decimal_places=2
    )


class DashboardCSATScoreByAgentsSerializer(serializers.Serializer):
    agent = serializers.SerializerMethodField()
    rooms = serializers.SerializerMethodField()
    reviews = serializers.IntegerField()
    avg_rating = serializers.DecimalField(
        allow_null=True, max_digits=3, decimal_places=2
    )

    def get_agent(self, obj):
        name = f"{obj.get('first_name')} {obj.get('last_name')}".strip()

        return {
            "name": name,
            "email": obj.get("email"),
        }

    def get_rooms(self, obj):
        return obj.get("rooms_count")
