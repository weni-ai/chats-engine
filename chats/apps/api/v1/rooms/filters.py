from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from chats.apps.rooms.models import Room
from chats.core.cache_utils import get_user_id_by_email_cached
from chats.apps.projects.models.models import ProjectPermission

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

    room_status = filters.CharFilter(
        field_name="room_status",
        required=False,
        method="filter_room_status",
        help_text=_("Room status"),
    )

    def filter_room_status(self, queryset, name, value):
        if value == "ongoing":
            return queryset.filter(user__isnull=False, is_waiting=False)
        elif value == "waiting":
            return queryset.filter(user__isnull=True, is_waiting=False)
        elif value == "flow_start":
            return queryset.filter(is_waiting=True)
        return queryset

    def filter_project(self, queryset, name, value):
        try:
            project_permission = self.request.user.project_permissions.get(
                project__uuid=value
            )
        except ObjectDoesNotExist:
            return queryset.none()

        request_params = getattr(self.request, "query_params", None)
        if request_params is None:
            request_params = getattr(self.request, "GET", {})

        user_param = request_params.get("email") or self.request.user
        if isinstance(user_param, User):
            user_email = (user_param.email or "").lower()
        else:
            user_email = (user_param or "").lower()
            uid = get_user_id_by_email_cached(user_email)
            if uid is None:
                return queryset.none()
            project_permission = ProjectPermission.objects.get(
                user_id=user_email, project__uuid=value
            )

        if project_permission.is_admin:
            user_filter = Q(user_id=user_email) | Q(user__isnull=True)
            return queryset.filter(
                user_filter, is_active=True, queue__in=project_permission.queue_ids
            )
        user_project = Q(user_id=user_email) & Q(project_uuid=value)
        queue_filter = Q(user__isnull=True) & Q(queue__in=project_permission.queue_ids)
        ff = user_project | queue_filter

        queryset = queryset.filter(
            ff,
            is_active=True,
        )
        return queryset

    def filter_is_active(self, queryset, name, value):
        return queryset.filter(is_active=value)
