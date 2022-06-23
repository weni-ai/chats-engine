from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from chats.apps.api.v1.sectors.serializers import SectorSerializer
from chats.apps.sectors.models import Sector


class SectorViewset(viewsets.ModelViewSet):
    queryset = Sector.objects
    serializer_class = SectorSerializer
    permission_classes = [
        IsAuthenticated,
    ]
