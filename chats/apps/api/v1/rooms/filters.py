from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from chats.apps.rooms.models import Room

User = get_user_model()


class RoomFilter(filters.FilterSet):
    class Meta:
        model = Room
        fields = ["queue", "is_waiting"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Project's UUID"),
    )

    attending = filters.BooleanFilter(
        required=False,
        method="filter_attending",
    )

    def filter_project(self, queryset, name, value):
        try:
            project_permission = self.request.user.project_permissions.get(
                project__uuid=value
            )
        except ObjectDoesNotExist:
            return queryset.none()
        user = self.request.query_params.get("email") or self.request.user

        if type(user) is str:
            user = User.objects.get(email=user)
            project_permission = user.project_permissions.get(project__uuid=value)

        if project_permission.is_admin:
            user_filter = Q(user=user) | Q(user__isnull=True)
            return queryset.filter(user_filter, queue__in=project_permission.queue_ids)
        user_project = Q(user=user) & Q(project_uuid=value)
        queue_filter = Q(user__isnull=True) & Q(queue__in=project_permission.queue_ids)
        ff = user_project | queue_filter
        queryset = queryset.filter(
            ff,
        )
        return queryset

    def filter_attending(self, queryset, name, value):
        return queryset.filter(user__isnull=not value)
