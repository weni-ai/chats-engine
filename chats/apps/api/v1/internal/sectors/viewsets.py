from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from chats.apps.sectors.models import SectorTag
from chats.apps.api.internal.sectors.serializers import SectorTagSerializer


class SectorTagsViewset(viewsets.ModelViewSet):
    queryset = SectorTag.objects.all()
    serializer_class = SectorTagSerializer
    filter_backends = [DjangoFilterBackend]
    permission_classes = [
        IsAuthenticated,
    ]
    lookup_field = "uuid"