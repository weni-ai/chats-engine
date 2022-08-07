from django.db.models import Q

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.contacts.models import Contact
from chats.apps.api.v1.contacts.filters import ContactFilter


class ContactViewset(
    viewsets.GenericViewSet,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
):

    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ContactFilter
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        is_manager = Q(rooms__queue__sector__authorizations__user=user)
        is_admin = Q(
            Q(rooms__queue__sector__project__authorizations__user=user)
            & Q(rooms__queue__sector__project__authorizations__role=1)
        )
        is_user_assigned_to_room = Q(rooms__user=user)

        check_admin_manager_agent_role_filter = (
            is_manager | is_admin | is_user_assigned_to_room
        )
        user_role_related_contacts = qs.filter(check_admin_manager_agent_role_filter)
        return user_role_related_contacts
