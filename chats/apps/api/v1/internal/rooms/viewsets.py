from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import LimitOffsetPagination

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.internal.rooms.serializers import RoomInternalListSerializer
from chats.apps.rooms.models import Room

from .filters import RoomFilter


class InternalListRoomsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomInternalListSerializer
    lookup_field = "uuid"
    permission_classes = [permissions.IsAuthenticated, ModuleHasPermission]

    filter_backends = [
        filters.OrderingFilter,
        filters.SearchFilter,
        DjangoFilterBackend,
    ]
    ordering = ["-created_on"]
    search_fields = [
        "contact__external_id",
        "contact__name",
        "user__email",
        "urn",
    ]
    filterset_class = RoomFilter

    pagination_class = LimitOffsetPagination
    pagination_class.page_size = 5

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Pega o parâmetro sector da URL
        sector_param = self.request.query_params.get('sector')
        
        # Se encontrou o parâmetro e ele contém vírgulas, vamos tratar manualmente
        if sector_param and ',' in sector_param:
            # Remove o parâmetro sector da query para evitar processamento duplo
            request_copy = self.request._request
            query_params = request_copy.GET.copy()
            if 'sector' in query_params:
                del query_params['sector']
            request_copy.GET = query_params
            
            # Divide os setores em uma lista
            sector_ids = [s.strip() for s in sector_param.split(',') if s.strip()]
            
            # Aplica o filtro diretamente
            if sector_ids:
                queryset = queryset.filter(queue__sector__in=sector_ids)
        
        return queryset
