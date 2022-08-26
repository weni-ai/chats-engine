from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from chats.apps.msgs.models import MessageMedia, Message
from django.db.models import Q


class MessageFilter(filters.FilterSet):
    class Meta:
        model = Message
        fields = ["contact", "room"]

    contact = filters.UUIDFilter(
        field_name="contact",
        required=False,
        method="filter_contact",
        help_text=_("Contact's UUID"),
    )

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
        help_text=_("Projects's UUID"),
    )

    is_active = filters.BooleanFilter(
        field_name="is_active",
        required=False,
        method="filter_is_active",
        help_text=_("Is room active"),
    )

    def filter_room(self, queryset, name, value):
        return queryset.filter(room__uuid=value)

    def filter_is_active(self, queryset, name, value):
        return queryset.filter(room__is_active=value)

    def filter_project(self, queryset, name, value):
        return queryset.filter(room__queue__sector__project__uuid=value)

    def filter_contact(self, queryset, name, value):
        """
        Return msgs given a contact.
        Check if the user requesting has permition on the sector or project
        """
        user = self.request.user

        # Check if the user requesting has permition on the sector or project
        # querry_filters = (
        #     Q(room__queue__authorizations__permission__user=user)
        #     | Q(room__queue__sector__authorizations__permission__user=user)
        #     | Q(
        #         Q(room__queue__sector__project__permissions__user=user)
        #         & Q(room__queue__sector__project__permissions__role=2)
        #     )
        # )
        queryset = queryset.filter(
            room__queue__sector__project__permissions__user=user,
            room__contact__uuid=value,
        )

        return queryset


class MessageMediaFilter(filters.FilterSet):
    class Meta:
        model = MessageMedia
        fields = ["message"]

    contact = filters.UUIDFilter(
        field_name="contact",
        required=False,
        method="filter_contact",
        help_text=_("Contact's UUID"),
    )

    room = filters.UUIDFilter(
        field_name="room",
        required=False,
        method="filter_room",
        help_text=_("Room's UUID"),
    )

    def filter_contact(self, queryset, name, value):
        """
        Return medias given a contact, using the contact rooms for the search
        """
        queryset = queryset.filter(message__room__contact__uuid=value)

        return queryset

    def filter_room(self, queryset, name, value):
        """
        Return medias given a contact, using the contact rooms for the search
        """
        queryset = queryset.filter(message__room__uuid=value)

        return queryset
