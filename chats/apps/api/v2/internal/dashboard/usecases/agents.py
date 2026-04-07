from django.db.models import Q

from chats.apps.api.v1.dashboard.dto import should_exclude_admin_domains
from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.service import AgentsService
from chats.apps.api.v1.internal.dashboard.viewsets import _build_status_filter
from chats.apps.projects.models.models import CustomStatus, Project


class InternalDashboardAgentsUsecase:
    def execute(self, project: Project, filters: dict):
        user_request = filters.get("user_request", "")

        dto = Filters(
            start_date=filters.get("start_date"),
            end_date=filters.get("end_date"),
            agent=filters.get("agent"),
            sector=filters.get("sector"),
            tag=filters.get("tag"),
            queues=filters.get("queue"),
            user_request=user_request,
            is_weni_admin=should_exclude_admin_domains(user_request),
            ordering=filters.get("ordering"),
        )

        agents_data = AgentsService().get_agents_data(
            dto, project, include_removed=True
        )

        has_filter = False
        combined_q = Q()

        status_filter = _build_status_filter(filters.get("status", []))
        if status_filter is not None:
            combined_q |= status_filter
            has_filter = True

        custom_status_names = filters.get("custom_status", [])
        if custom_status_names:
            has_filter = True
            custom_emails = list(
                CustomStatus.objects.filter(
                    status_type__name__in=custom_status_names,
                    is_active=True,
                    project=project,
                ).values_list("user", flat=True)
            )
            if custom_emails:
                combined_q |= Q(email__in=custom_emails)
            else:
                combined_q |= Q(pk__in=[])

        if has_filter:
            agents_data = agents_data.filter(combined_q)

        return agents_data
