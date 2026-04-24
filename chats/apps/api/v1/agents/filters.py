from django.db.models import Exists, OuterRef, Q
from django_filters import rest_framework as filters

from chats.apps.projects.models import ProjectPermission
from chats.apps.projects.models.models import CustomStatus


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    pass


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class AllAgentsFilter(filters.FilterSet):
    status = CharInFilter(method="filter_status")
    custom_status = CharInFilter(method="filter_custom_status")
    agent = CharInFilter(method="filter_agent")
    sector = UUIDInFilter(method="filter_sector")
    queue = UUIDInFilter(method="filter_queue")

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

    def filter_status(self, queryset, name, values):
        if not values:
            return queryset

        normalized = {v.lower() for v in values if v}
        qs = queryset.annotate(_on_pause=Exists(self._active_pause_qs()))

        condition = Q()
        if "online" in normalized:
            condition |= Q(status=ProjectPermission.STATUS_ONLINE, _on_pause=False)
        if "offline" in normalized:
            condition |= Q(status=ProjectPermission.STATUS_OFFLINE)

        if not condition:
            return queryset

        return qs.filter(condition)

    def filter_custom_status(self, queryset, name, values):
        if not values:
            return queryset

        project_uuid = self.request.resolver_match.kwargs.get("project_uuid")
        return queryset.filter(
            user__user_custom_status__is_active=True,
            user__user_custom_status__status_type__name__in=values,
            user__user_custom_status__project__uuid=project_uuid,
        ).distinct()

    def filter_agent(self, queryset, name, values):
        if not values:
            return queryset

        condition = Q()
        for value in values:
            if value:
                condition |= Q(user__email__icontains=value)

        if not condition:
            return queryset

        return queryset.filter(condition).distinct()

    def filter_sector(self, queryset, name, values):
        if not values:
            return queryset
        return queryset.filter(
            queue_authorizations__queue__sector__uuid__in=values,
            queue_authorizations__queue__is_deleted=False,
            queue_authorizations__queue__sector__is_deleted=False,
        ).distinct()

    def filter_queue(self, queryset, name, values):
        if not values:
            return queryset
        return queryset.filter(
            queue_authorizations__queue__uuid__in=values,
            queue_authorizations__queue__is_deleted=False,
            queue_authorizations__queue__sector__is_deleted=False,
        ).distinct()
