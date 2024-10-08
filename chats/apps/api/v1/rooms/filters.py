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
            return queryset.filter(
                user_filter, is_active=True, queue__in=project_permission.queue_ids
            )
        user_project = Q(user=user) & Q(project_uuid=value)
        queue_filter = Q(user__isnull=True) & Q(queue__in=project_permission.queue_ids)
        ff = user_project | queue_filter
        queryset = queryset.filter(
            ff,
            is_active=True,
        )
        return queryset

    def filter_is_active(self, queryset, name, value):
        return queryset.filter(is_active=value)
