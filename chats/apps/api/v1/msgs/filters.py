from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from chats.apps.msgs.models import MessageMedia, Message
from django.db.models import Q


class MessageFilter(filters.FilterSet):
    class Meta:
        model = Message
        fields = ["contact"]

    contact = filters.UUIDFilter(
        field_name="contact",
        required=False,
        method="filter_contact",
        help_text=_("Contact's UUID"),
    )

    def filter_contact(self, queryset, name, value):
        """
        Return msgs given a contact.
        Check if the user requesting has permition on the sector or project
        """
        user = self.request.user

        # Check if the user requesting has permition on the sector or project
        querry_filters = (
            Q(room__queue__authorizations__permission__user=user)
            | Q(room__queue__sector__authorizations__permission__user=user)
            | Q(
                Q(room__queue__sector__project__permissions__user=user)
                & Q(room__queue__sector__project__permissions__role=2)
            )
        )
        queryset = queryset.filter(querry_filters)

        return queryset


class MessageMediaFilter(filters.FilterSet):
    class Meta:
        model = MessageMedia
        fields = ["contact"]

    contact = filters.UUIDFilter(
        field_name="contact",
        required=False,
        method="filter_contact",
        help_text=_("Contact's UUID"),
    )

    def filter_contact(self, queryset, name, value):
        """
        Return medias given a contact, using the contact rooms for the search
        """
        queryset = queryset.filter(message__room__contact__uuid=value)

        return queryset
