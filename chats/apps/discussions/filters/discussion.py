from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from ..models import Discussion

User = get_user_model()


class DiscussionFilter(filters.FilterSet):
    class Meta:
        model = Discussion
        fields = ["room", "is_active"]

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Projects's UUID"),
    )

    def filter_project(self, queryset, name, value):
        if self.request.query_params.get("room"):
            return queryset.filter(queue__sector__project=value)

        user = self.request.query_params.get("email") or self.request.user
        if type(user) == str:
            user = User.objects.get(email=user)

        permission = user.project_permissions.get(project=value)
        queryset = queryset.filter(
            Q(added_users__permission=permission) | Q(is_queued=True)
        )

        if permission.is_admin:
            return queryset.filter(queue__sector__project=value)
        return queryset.filter(
            queue__in=permission.queue_ids,
        ).distinct()  # return only the discussions the user has access
