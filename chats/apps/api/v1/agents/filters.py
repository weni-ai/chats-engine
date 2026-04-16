from django.db.models import Exists, OuterRef
from django_filters import rest_framework as filters

from chats.apps.projects.models import ProjectPermission
from chats.apps.projects.models.models import CustomStatus


class AllAgentsFilter(filters.FilterSet):
    status = filters.CharFilter(method="filter_status")
    custom_status = filters.CharFilter(method="filter_custom_status")
    agent = filters.CharFilter(method="filter_agent")
    sector = filters.UUIDFilter(method="filter_sector")
    queue = filters.UUIDFilter(method="filter_queue")

    class Meta:
        model = ProjectPermission
        fields = []

    def _active_pause_qs(self):
        """Subquery: agent has an active non-in-service CustomStatus in the same project."""
        return CustomStatus.objects.filter(
            user_id=OuterRef("user_id"),
            project=OuterRef("project"),
            is_active=True,
        ).exclude(status_type__name__iexact="in-service")

    def filter_status(self, queryset, name, value):
        if value.lower() == "online":
            return queryset.annotate(_on_pause=Exists(self._active_pause_qs())).filter(
                status=ProjectPermission.STATUS_ONLINE, _on_pause=False
            )
        if value.lower() == "offline":
            return queryset.filter(status=ProjectPermission.STATUS_OFFLINE)
        return queryset

    def filter_custom_status(self, queryset, name, value):
        project_uuid = self.request.resolver_match.kwargs.get("project_uuid")
        return queryset.filter(
            user__user_custom_status__is_active=True,
            user__user_custom_status__status_type__name__iexact=value,
            user__user_custom_status__project__uuid=project_uuid,
        )

    def filter_agent(self, queryset, name, value):
        return queryset.filter(user__email__icontains=value)

    def filter_sector(self, queryset, name, value):
        return queryset.filter(
            queue_authorizations__queue__sector__uuid=value
        ).distinct()

    def filter_queue(self, queryset, name, value):
        return queryset.filter(queue_authorizations__queue__uuid=value).distinct()
