from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings

from chats.apps.api.authentication.classes import JWTAuthentication
from chats.apps.api.authentication.permissions import (
    HasInternalAuthenticationPermission,
)
from chats.apps.api.v1.internal.contacts.filters import RoomsContactsInternalFilter
from chats.apps.api.v1.internal.contacts.serializers import (
    RoomsContactsInternalSerializer,
)
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.contacts.models import Contact
from chats.apps.api.pagination import CustomCursorPagination


class RoomsContactsInternalViewSet(ListModelMixin, GenericViewSet):
    queryset = Contact.objects.all()
    serializer_class = RoomsContactsInternalSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = RoomsContactsInternalFilter
    authentication_classes = [
        JWTAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    search_fields = ["name"]
    ordering = ["-created_on"]
    ordering_fields = ["name", "created_on"]
    pagination_class = CustomCursorPagination

    def get_permissions(self):
        if getattr(self.request, "jwt_payload", None):
            return [HasInternalAuthenticationPermission()]
        return [IsAuthenticated(), ModuleHasPermission()]
