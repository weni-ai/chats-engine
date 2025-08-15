from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from chats.apps.projects.models.models import ProjectPermission
from chats.core.cache_utils import get_user_id_by_email_cached

from ..models import Discussion

User = get_user_model()


class DiscussionFilter(filters.FilterSet):
    class Meta:
        model = Discussion
        fields = ["room", "is_active", "subject"]

    search = filters.CharFilter(
        method="filter_search",
        help_text=_("Filter discussions by subject or contact's name"),
    )

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Projects's UUID"),
    )

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(subject__icontains=value) | Q(room__contact__name__icontains=value)
        )

    def filter_project(self, queryset, name, value):
        if self.request.query_params.get("room") and not self.request.query_params.get(
            "is_active"
        ):
            return queryset.filter(queue__sector__project=value)

        user_param = self.request.query_params.get("email") or self.request.user
        if isinstance(user_param, User):
            user_email = (user_param.email or "").lower()
        else:
            user_email = (user_param or "").lower()
            uid = get_user_id_by_email_cached(user_email)
            if uid is None:
                return queryset.none()

        permission = ProjectPermission.objects.get(project=value, user_id=user_email)

        queues_filter = (
            Q(queue__sector__project=value)
            if permission.is_admin
            else Q(queue__in=permission.queue_ids)
        )

        return queryset.filter(
            (queues_filter & Q(is_queued=True)) | Q(added_users__permission=permission)
        ).distinct()
