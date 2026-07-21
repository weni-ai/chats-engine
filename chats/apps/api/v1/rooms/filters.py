from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from weni.feature_flags.shortcuts import is_feature_active

from chats.apps.api.v1.msgs.enums import MessageMediaContentTypesFilterParams
from chats.apps.projects.models.models import ProjectPermission
from chats.apps.rooms.models import Room, RoomNoteMedia
from chats.core.cache_utils import get_user_id_by_email_cached

User = get_user_model()


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    pass


class RoomFilter(filters.FilterSet):
    class Meta:
        model = Room
        fields = ["queue", "is_active"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Project UUID"),
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

    queues = UUIDInFilter(
        field_name="queue__uuid",
        method="filter_queues",
        help_text=_("Filter by multiple queue UUIDs (comma-separated)"),
    )

    sectors = UUIDInFilter(
        field_name="queue__sector__uuid",
        method="filter_sectors",
        help_text=_("Filter by multiple sector UUIDs (comma-separated)"),
    )

    def _multi_filter_enabled(self) -> bool:
        # Cache the flag check on the request so both `queues` and `sectors`
        # share a single call per request.
        cached = getattr(self.request, "_rooms_multi_filter_flag", None)
        if cached is not None:
            return cached

        request_params = getattr(self.request, "query_params", None) or getattr(
            self.request, "GET", {}
        )
        project = request_params.get("project")
        user_email = getattr(getattr(self.request, "user", None), "email", None)

        if not project or not user_email:
            result = False
        else:
            try:
                result = is_feature_active(
                    settings.ROOMS_COUNT_BY_QUEUE_FEATURE_FLAG_KEY,
                    user_email,
                    str(project),
                )
            except Exception:
                result = False

        self.request._rooms_multi_filter_flag = result
        return result

    def filter_queues(self, queryset, name, value):
        if not self._multi_filter_enabled():
            return queryset
        return queryset.filter(queue__uuid__in=value)

    def filter_sectors(self, queryset, name, value):
        if not self._multi_filter_enabled():
            return queryset
        return queryset.filter(queue__sector__uuid__in=value)

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


class RoomNoteMediaFilter(filters.FilterSet):
    class Meta:
        model = RoomNoteMedia
        fields = ["note"]

    room = filters.UUIDFilter(
        field_name="room",
        required=False,
        method="filter_room",
        help_text=_("Room's UUID"),
    )

    project = filters.UUIDFilter(
        field_name="project",
        required=False,
        method="filter_project",
        help_text=_("Project's UUID"),
    )

    content_type = filters.CharFilter(
        field_name="content_type",
        required=False,
        method="filter_content_type",
        help_text=_("Content type"),
    )

    def filter_room(self, queryset, name, value):
        return queryset.filter(note__room__uuid=value)

    def filter_project(self, queryset, name, value):
        return queryset.filter(note__room__queue__sector__project__uuid=value)

    def filter_content_type(self, queryset, name, value):
        if value == MessageMediaContentTypesFilterParams.AUDIO:
            return queryset.filter(content_type__startswith="audio")
        elif value == MessageMediaContentTypesFilterParams.MEDIA:
            return queryset.filter(
                Q(content_type__startswith="image")
                | Q(content_type__startswith="video")
            )
        elif value == MessageMediaContentTypesFilterParams.DOCUMENTS:
            return queryset.filter(
                ~Q(content_type__startswith="image")
                & ~Q(content_type__startswith="video")
                & ~Q(content_type__startswith="audio")
            )

        return queryset
