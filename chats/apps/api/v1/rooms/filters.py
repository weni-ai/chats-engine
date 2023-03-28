from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django_filters import rest_framework as filters
from chats.apps.projects.models import Project
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue


class RoomFilter(filters.FilterSet):
    class Meta:
        model = Room
        fields = ["queue", "is_active"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Project's UUID"),
    )

    is_active = filters.BooleanFilter(
        field_name="is_active",
        required=False,
        method="filter_is_active",
        help_text=_("Is active?"),
    )

    def filter_project(self, queryset, name, value):
        project_permission = self.request.user.project_permissions.get(
            project__uuid=value
        )
        if project_permission.is_admin:
            user_filter = Q(user=self.request.user) | Q(user__isnull=True)
            return queryset.filter(
                user_filter, is_active=True, queue__in=project_permission.queue_ids
            ).order_by(
                "user", "created_on"
            )  # TODO: THIS IS A HOTFIX, REMOVE THIS ORDER AND USE THE VIEW ORDERING
        user_project = Q(user=self.request.user) & Q(queue__sector__project__uuid=value)
        queue_filter = Q(user__isnull=True) & Q(
            queue__uuid__in=project_permission.queue_ids
        )
        ff = user_project | queue_filter
        queryset = queryset.filter(
            ff,
            is_active=True,
        )
        return queryset.order_by(
            "user", "created_on"
        )  # TODO: THIS IS A HOTFIX, REMOVE THIS ORDER AND USE THE VIEW ORDERING

    def filter_is_active(self, queryset, name, value):
        return queryset.filter(is_active=value)
