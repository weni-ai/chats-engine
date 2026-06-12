from django.conf import settings
from django.core.cache import cache
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v2.quickmessages.cache import get_list_user_qm_cache_key
from chats.apps.api.v2.quickmessages.pagination import QuickMessageCursorPagination
from chats.apps.api.v2.quickmessages.serializers import QuickMessageResponseSerializer
from chats.apps.quickmessages.models import QuickMessage


class QuickMessageViewSetV2(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = QuickMessageResponseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = QuickMessageCursorPagination
    lookup_field = "uuid"

    def get_queryset(self):
        return QuickMessage.objects.filter(sector__isnull=True)

    def list(self, request, *args, **kwargs):
        cursor = request.query_params.get("cursor", "")
        limit = request.query_params.get("limit", "")

        cache_key = get_list_user_qm_cache_key(cursor=cursor, limit=limit)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, settings.QUICK_MESSAGES_CACHE_TTL)
        return response
