from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import exceptions

from chats.apps.rooms.models import Room


class HistoryRoomFilter(filters.FilterSet):
    class Meta:
        model = Room
        fields = []

    contact = filters.CharFilter(
        field_name="contact__external_id",
        required=False,
        help_text=_("Contact's External ID"),
    )

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Projects's UUID"),
    )

    sector = filters.CharFilter(
        field_name="queue__sector__uuid",
        required=False,
        help_text=_("Sector's UUID"),
    )

    tag = filters.CharFilter(
        required=False,
        method="filter_tags",
        help_text=_("Room Tags"),
    )
    created_on = filters.DateFromToRangeFilter(
        field_name="created_on",
        required=False,
        lookup_expr="date",
        help_text=_("Room created on"),
    )
    ended_at = filters.DateFromToRangeFilter(
        field_name="ended_at",
        required=False,
        lookup_expr="date",
        help_text=_("Room ended at"),
    )

    def filter_project(self, queryset, name, value):
        user = self.request.user

        try:
            user_permission = user.project_permissions.select_related("project").get(
                project=value
            )
        except ObjectDoesNotExist:
            raise exceptions.APIException(
                detail="Access denied! Make sure you have the right permission to access this project"
            )

        base_queryset = queryset.filter(is_active=False, ended_at__isnull=False)

        project = user_permission.project
        contacts_blocklist = project.history_contacts_blocklist
        if contacts_blocklist:
            base_queryset = base_queryset.exclude(
                contact__external_id__in=contacts_blocklist
            )

        if (
            user_permission.is_admin is False
            and project.agents_can_see_queue_history is False
        ):
            return base_queryset.filter(user=user, queue__sector__project=value)

        queue_ids = user_permission.queue_ids
        return base_queryset.filter(
            Q(queue__in=queue_ids) | Q(user=user, queue__sector__project=value)
        )

    def filter_sector(self, queryset, name, value):
        return queryset

    def filter_tags(self, queryset, name, value):
        if not value:
            return queryset

        values = value.split(",")
        return queryset.filter(tags__name__in=values).distinct()

    def filter_contact(self, queryset, name, value):
        return queryset
