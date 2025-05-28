from chats.apps.api.utils import calculate_in_service_time
from rest_framework import serializers


class DashboardAgentsSerializer(serializers.Serializer):
    link = serializers.SerializerMethodField()
    opened = serializers.IntegerField(allow_null=True, required=False)
    agent = serializers.SerializerMethodField()
    closed = serializers.IntegerField(allow_null=True, required=False)
    status = serializers.SerializerMethodField()

    def get_link(self, obj):
        return {
            "url": f"chats:dashboard/view-mode/{obj.get('email', '')}",
            "type": "internal",
        }

    def get_status(self, obj):
        custom_status_list = obj.get("custom_status") or []

        if custom_status_list:
            for status_item in custom_status_list:
                print(f"DEBUG - Custom status item: {status_item}")
                status_type = status_item.get("status_type")
                break_time = status_item.get("break_time", 0)
                is_active = status_item.get("is_active", False)

                if status_type != "In-Service" and is_active:
                    return {"status": "orange", "label": status_type}

        if obj.get("status") == "ONLINE":
            return {"status": "green", "label": None}
        elif obj.get("status") == "OFFLINE":
            return {"status": "gray", "label": None}

        return {"status": "gray", "label": None}

    def get_agent(self, obj):
        return f"{obj.get('first_name')} {obj.get('last_name')}"


class DashboardCustomAgentStatusSerializer(serializers.Serializer):
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
        custom_status_list = obj.get("custom_status") or []

        if custom_status_list:
            for status_item in custom_status_list:
                print(f"DEBUG - Custom status item: {status_item}")
                status_type = status_item.get("status_type")
                break_time = status_item.get("break_time", 0)
                is_active = status_item.get("is_active", False)

                if status_type != "In-Service" and is_active:
                    return {"status": "orange", "label": status_type}

        if obj.get("status") == "ONLINE":
            return {"status": "green", "label": None}
        elif obj.get("status") == "OFFLINE":
            return {"status": "gray", "label": None}

        return {"status": "gray", "label": None}

    def get_agent(self, obj):
        return f"{obj.get('first_name')} {obj.get('last_name')}"

    def get_custom_status(self, obj):
        custom_status_list = obj.get("custom_status") or []
        
        # DEBUG: Ver EXATAMENTE quais registros chegaram
        in_service_records = [s for s in custom_status_list if s.get("status_type") == "In-Service"]
        
        print(f"=== DEBUG {obj.get('email')} ===")
        print(f"Total registros In-Service recebidos: {len(in_service_records)}")
        for i, record in enumerate(in_service_records):
            print(f"  {i+1}. break_time: {record.get('break_time')}, is_active: {record.get('is_active')}")
        
        in_service_time = calculate_in_service_time(custom_status_list)
        print(f"Tempo calculado: {in_service_time} segundos = {in_service_time/60:.1f} minutos")
        print("=== FIM DEBUG ===")
        
        project = self.context.get("project")
        all_status_types = project.custom_statuses.filter(is_deleted=False).values_list(
            "name", flat=True
        )

        # Criar dicionário para os tempos acumulados de break_time
        status_dict = {status_type: 0 for status_type in all_status_types}

        # Processar tempos de break_time para todos os status exceto In-Service
        if custom_status_list:
            for status_item in custom_status_list:
                status_type = status_item.get("status_type")
                break_time = status_item.get("break_time", 0)
                if status_type in status_dict and status_type != "In-Service":
                    status_dict[status_type] += break_time

        # Definir o valor de In-Service com o tempo calculado
        if "In-Service" in status_dict:
            status_dict["In-Service"] = in_service_time

        # Criar a lista de resultados
        result = [
            {"status_type": status_type, "break_time": break_time}
            for status_type, break_time in status_dict.items()
        ]

        return result