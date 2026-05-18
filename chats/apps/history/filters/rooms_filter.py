from django.db.models import QuerySet
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import exceptions

from chats.apps.contacts.models import Contact, normalize_document
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
        method="filter_contact_identifiers",
        help_text=_("Contact's External ID"),
    )

    email = filters.CharFilter(
        required=False,
        method="filter_contact_identifiers",
        help_text=_(
            "Contact's email. Combined with `contact` and `document` to unify "
            "the history of the same person across channels."
        ),
    )

    document = filters.CharFilter(
        required=False,
        method="filter_contact_identifiers",
        help_text=_(
            "Contact's document (e.g. CPF). Punctuation is ignored. Combined "
            "with `contact` and `email` to unify the history of the same "
            "person across channels."
        ),
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

        return filter_history_rooms_queryset_by_project_permission(
            queryset, user_permission
        )

    def filter_tags(self, queryset, name, value):
        if not value:
            return queryset

        values = value.split(",")
        return queryset.filter(tags__name__in=values).distinct()

    def filter_contact_identifiers(self, queryset, name, value):
        """
        Unified handler for `contact`, `email` and `document` query params.

        Each of the three filters routes to this method; the actual lookup is
        applied once per request by reading every relevant value from the
        cleaned form data. This is what powers the "Ver histórico" button:
        the frontend sends the contact's external_id, email and document
        (whichever are available) and the backend returns rooms from every
        Contact that matches any of those identifiers — even when the same
        person has multiple Contact rows (e.g. WhatsApp + Telegram + web
        chat sessions with rotating URNs).
        """
        if getattr(self, "_contact_identifiers_applied", False):
            return queryset
        self._contact_identifiers_applied = True

        cleaned = getattr(self.form, "cleaned_data", {}) or {}
        external_id = (cleaned.get("contact") or "").strip()
        email = (cleaned.get("email") or "").strip()
        document = normalize_document((cleaned.get("document") or "").strip())

        contact_filters = []
        if external_id:
            contact_filters.append(Q(external_id=external_id))
        if email:
            contact_filters.append(Q(email__iexact=email))
        if document:
            contact_filters.append(Q(document=document))

        if not contact_filters:
            return queryset

        combined = contact_filters[0]
        for extra in contact_filters[1:]:
            combined |= extra

        seed_contacts = list(Contact.objects.filter(combined))

        if not seed_contacts:
            # Legacy fallback: when only `contact` is provided and no Contact
            # matches the external_id, keep the previous behavior of filtering
            # rooms by `contact__external_id` (returns zero rooms in practice,
            # but preserves the pre-existing contract).
            if external_id and not email and not document:
                return queryset.filter(contact__external_id=external_id)
            return queryset.none()

        # Expansion: include other Contacts that share email/document with
        # any of the seeds, so we cover cases where only one identifier was
        # provided but the underlying Contact has more identifiers stored.
        expansion = Q(pk__in=[c.pk for c in seed_contacts])
        for seed_email in {c.email for c in seed_contacts if c.email}:
            expansion |= Q(email__iexact=seed_email)
        seed_documents = {c.document for c in seed_contacts if c.document}
        if seed_documents:
            expansion |= Q(document__in=seed_documents)

        related_pks = set(
            Contact.objects.filter(expansion).values_list("pk", flat=True)
        )
        return queryset.filter(contact_id__in=related_pks)
