from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from chats.apps.api.v1.contacts.filters import ContactFilter
from chats.apps.api.v1.contacts.serializers import ContactViewsetSerializer
from chats.apps.contacts.models import Contact


class ContactViewset(viewsets.ReadOnlyModelViewSet):

    queryset = Contact.objects.all()
    serializer_class = ContactViewsetSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ContactFilter
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "rooms__urn"]
    ordering = ["-last_ended_at"]

    def retrieve(self, request, *args, **kwargs):
        contact = self.get_object()
        contact.can_retrieve(request.user, request.query_params.get("project"))
        return super().retrieve(request, *args, **kwargs)
