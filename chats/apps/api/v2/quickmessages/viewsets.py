from django.conf import settings
from django.core.cache import cache
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v2.quickmessages.cache import get_list_cache_key
from chats.apps.api.v2.quickmessages.pagination import QuickMessageCursorPagination
from chats.apps.api.v2.quickmessages.permissions import (
    SectorQuickMessageProjectPermission,
)
from chats.apps.api.v2.quickmessages.serializers import (
    SectorQuickMessageQueryParamsSerializer,
    SectorQuickMessageResponseSerializer,
)
from chats.apps.quickmessages.models import QuickMessage


class SectorQuickMessageViewSetV2(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SectorQuickMessageResponseSerializer
    permission_classes = [IsAuthenticated, SectorQuickMessageProjectPermission]
    pagination_class = QuickMessageCursorPagination
    lookup_field = "uuid"

    def get_queryset(self):
        queryset = QuickMessage.objects.filter(
            sector__isnull=False
        ).select_related("sector")

        if self.action != "list":
            return queryset

        params_serializer = SectorQuickMessageQueryParamsSerializer(
            data=self.request.query_params
        )
        params_serializer.is_valid(raise_exception=True)
        params = params_serializer.validated_data

        sector_uuid = params.get("sector")
        project_uuid = params.get("project")

        if sector_uuid:
            queryset = queryset.filter(sector=sector_uuid)
        elif project_uuid:
            queryset = queryset.filter(sector__project=project_uuid)

        return queryset

    def list(self, request, *args, **kwargs):
        params_serializer = SectorQuickMessageQueryParamsSerializer(
            data=request.query_params
        )
        params_serializer.is_valid(raise_exception=True)
        params = params_serializer.validated_data

        sector_uuid = str(params.get("sector", ""))
        project_uuid = str(params.get("project", ""))
        cursor = request.query_params.get("cursor", "")
        limit = request.query_params.get("limit", "")

        cache_key = get_list_cache_key(
            sector_uuid=sector_uuid or None,
            project_uuid=project_uuid or None,
            cursor=cursor,
            limit=limit,
        )

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        cache.set(
            cache_key,
            response.data,
            settings.SECTOR_QUICK_MESSAGES_CACHE_TTL,
        )
        return response
