from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.users import serializers
from chats.apps.api.v1.sectors.filters import (
    SectorFilter,
)
from chats.apps.accounts.models import Profile


class ProfileViewset(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = serializers.ProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        return super().get_queryset()

    def get_object(self):
        return self.request.user.profile
