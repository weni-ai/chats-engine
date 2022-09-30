from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets

from chats.apps.api.v1.contacts.filters import ContactFilter
from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.contacts.models import Contact


class ContactViewset(viewsets.ReadOnlyModelViewSet):  #

    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ContactFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        is_queue_agent = Q(rooms__queue__authorizations__permission__user=user)

        is_sector_manager = Q(
            rooms__queue__sector__authorizations__permission__user=user
        )

        is_project_admin = Q(
            Q(rooms__queue__sector__project__permissions__user=user)
            & Q(rooms__queue__sector__project__permissions__role=1)
        )

        is_user_assigned_to_room = Q(rooms__user=user)

        check_admin_manager_agent_role_filter = (
            is_queue_agent
            | is_sector_manager
            | is_project_admin
            | is_user_assigned_to_room
        )
        user_role_related_contacts = qs.filter(
            check_admin_manager_agent_role_filter, rooms__is_active=False
        ).distinct()
        # user_role_related_contacts = qs.filter(
        #     rooms__queue__sector__project__permissions__user=user,
        # )

        return user_role_related_contacts

    def retrieve(self, request, *args, **kwargs):
        contact = self.get_object()
        contact.can_retrieve(request.user, request.query_params.get("project"))
        return super().retrieve(request, *args, **kwargs)
