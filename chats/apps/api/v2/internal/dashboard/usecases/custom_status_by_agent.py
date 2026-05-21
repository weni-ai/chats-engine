from chats.apps.api.v1.dashboard.dto import should_exclude_admin_domains
from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.service import AgentsService
from chats.apps.projects.models.models import Project


class InternalDashboardCustomStatusByAgentUsecase:
    def execute(self, project: Project, filters: dict):
        user_request = filters.get("user_request", "")

        start_date = filters.get("start_date")
        end_date = filters.get("end_date")

        dto = Filters(
            start_date=str(start_date) if start_date else None,
            end_date=str(end_date) if end_date else None,
            agent=filters.get("agent"),
            sector=filters.get("sector"),
            tag=filters.get("tag"),
            queue=filters.get("queue"),
            user_request=user_request,
            is_weni_admin=should_exclude_admin_domains(user_request),
            ordering=filters.get("ordering"),
        )

        return AgentsService().get_agents_custom_status(
            dto, project, include_removed=True
        )
