from django.db.models import QuerySet
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import exceptions

from chats.apps.contacts.models import Contact
from chats.apps.rooms.models import Room
from chats.apps.projects.models import ProjectPermission
from chats.apps.accounts.models import User
from chats.apps.projects.models import Project


def get_related_contact_ids(contact: Contact) -> QuerySet:
    """
    Returns the primary keys of every Contact that should be treated as
    the same person as `contact`, matching by external_id, email or
    document (ignoring empty values).

    Used by the history feature to unify conversations from different
    Contact rows that share email or document (e.g. a web chat user that
    gets a new URN on every session but sends the same CPF).
    """
    filters = Q(pk=contact.pk)
    if contact.email:
        filters |= Q(email__iexact=contact.email)
    if contact.document:
        filters |= Q(document=contact.document)
    return Contact.objects.filter(filters).values_list("pk", flat=True)


def filter_history_rooms_queryset_by_project_permission(
    queryset: QuerySet[Room],
    user_permission: ProjectPermission,
) -> QuerySet[Room]:

    project: Project = user_permission.project
    user: User = user_permission.user
    base_queryset = queryset.filter(is_active=False, ended_at__isnull=False)

    contacts_blocklist = project.history_contacts_blocklist

    if contacts_blocklist:
        base_queryset = base_queryset.exclude(
            contact__external_id__in=contacts_blocklist
        )

    base_queryset = base_queryset.filter(queue__sector__project=project)

    if user_permission.is_admin is False:
        if project.agents_can_see_queue_history is False:
            return base_queryset.filter(user=user)

        return base_queryset.filter(
            Q(queue__in=user_permission.queue_ids) | Q(user=user)
        )

    return base_queryset


def get_history_rooms_queryset_by_contact(
    contact: Contact,
    user: User,
    project: Project,
) -> QuerySet[Room]:
    user_permission = ProjectPermission.objects.filter(
        user=user, project=project
    ).first()

    base_queryset = Room.objects.filter(
        contact_id__in=get_related_contact_ids(contact),
        is_active=False,
        ended_at__isnull=False,
    )

    if not user_permission:
        return base_queryset.none()

    return filter_history_rooms_queryset_by_project_permission(
        base_queryset, user_permission
    )


class HistoryRoomFilter(filters.FilterSet):
    class Meta:
        model = Room
        fields = []

    contact = filters.CharFilter(
        required=False,
        method="filter_contact",
        help_text=_("Contact's External ID"),
    )

    project = filters.CharFilter(
        field_name="project",
        required=True,
        method="filter_project",
        help_text=_("Project UUID"),
    )

    sector = filters.CharFilter(
        field_name="queue__sector__uuid",
        required=False,
        help_text=_("Department UUID"),
    )

    tag = filters.CharFilter(
        required=False,
        method="filter_tags",
        help_text=_("Room tags"),
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

        return filter_history_rooms_queryset_by_project_permission(
            queryset, user_permission
        )

    def filter_tags(self, queryset, name, value):
        if not value:
            return queryset

        values = value.split(",")
        return queryset.filter(tags__name__in=values).distinct()

    def filter_contact(self, queryset, name, value):
        """
        Expands the `?contact=<external_id>` lookup to also include rooms
        from any Contact that shares email or document with the one
        identified by the given external_id. Falls back to the simple
        external_id filter when no matching Contact is found, preserving
        the previous behavior.
        """
        if not value:
            return queryset

        contact = Contact.objects.filter(external_id=value).first()
        if not contact:
            return queryset.filter(contact__external_id=value)

        return queryset.filter(contact_id__in=get_related_contact_ids(contact))
