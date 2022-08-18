from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets

from chats.apps.api.v1.contacts.filters import ContactFilter
from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.contacts.models import Contact
from chats.apps.api.v1.contacts.permissions import ContactRelatedRetrievePermission


class ContactViewset(
    viewsets.GenericViewSet,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
):

    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ContactFilter
    permission_classes = [permissions.IsAuthenticated, ContactRelatedRetrievePermission]

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        is_sector_manager = Q(rooms__queue__sector__authorizations__user=user)

        is_project_admin = Q(
            Q(rooms__queue__sector__project__authorizations__user=user)
            & Q(rooms__queue__sector__project__authorizations__role=1)
        )

        is_user_assigned_to_room = Q(rooms__user=user)

        check_admin_manager_agent_role_filter = (
            is_sector_manager | is_project_admin | is_user_assigned_to_room
        )
        user_role_related_contacts = qs.filter(check_admin_manager_agent_role_filter)
        return user_role_related_contacts

    def retrieve(self, request, *args, **kwargs):
        contact = self.get_object()
        contact.can_retrieve(request.user, request.query_params.get("project"))
        return super().retrieve(request, *args, **kwargs)
