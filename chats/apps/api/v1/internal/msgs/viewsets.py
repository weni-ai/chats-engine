from django.conf import settings
from django.core.cache import cache
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.settings import api_settings

from chats.apps.api.authentication.classes import JWTAuthentication
from chats.apps.api.authentication.permissions import (
    HasInternalAuthenticationPermission,
)
from chats.apps.api.v1.external.msgs.serializers import (
    RoomHistoryMessageSerializer,
    RoomHistoryQuerySerializer,
)
from chats.apps.api.v1.external.msgs.viewsets import RoomHistoryMessagesPagination
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.msgs.exceptions import RoomNotFoundError, RoomStillActiveError
from chats.apps.msgs.usecases.build_reply_index_maps import (
    BuildReplyIndexCoreMapUseCase,
    BuildReplyIndexMapUseCase,
)
from chats.apps.msgs.usecases.get_room_messages_history import (
    GetRoomMessagesHistoryUseCase,
)
from chats.apps.msgs.utils import is_reply_core_fallback_active
from chats.apps.rooms.models import Room


class InternalRoomHistoryMessagesViewSet(viewsets.GenericViewSet):
    """
    Read-only endpoint that returns the message history of a closed room.

    Authenticated via internal JWT or module tokens. Internal notes are
    excluded at the database level. Responses are cached per ``(room, cursor)``
    for ``settings.ROOM_HISTORY_CACHE_TTL`` seconds.
    """

    swagger_tag = "Rooms"
    serializer_class = RoomHistoryMessageSerializer
    authentication_classes = [
        JWTAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    pagination_class = RoomHistoryMessagesPagination

    def get_permissions(self):
        if getattr(self.request, "jwt_payload", None):
            return [HasInternalAuthenticationPermission()]
        return [permissions.IsAuthenticated(), ModuleHasPermission()]

    @staticmethod
    def _cache_key(room_uuid: str, cursor: str) -> str:
        return f"internal:room_history:{room_uuid}:{cursor or ''}"

    def _resolve_project_uuid(self, request, room_uuid) -> str:
        project = getattr(request, "project", None)
        if project is not None:
            return str(project.uuid)

        return (
            Room.objects.filter(uuid=room_uuid)
            .values_list("project_uuid", flat=True)
            .first()
            or ""
        )

    @swagger_auto_schema(auto_schema=None)
    def list(self, request, *args, **kwargs):
        """List the message history of a closed room with cursor pagination."""
        query_serializer = RoomHistoryQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        room_uuid = query_serializer.validated_data["room"]

        cursor = request.query_params.get(
            RoomHistoryMessagesPagination.cursor_query_param, ""
        )
        cache_key = self._cache_key(str(room_uuid), cursor)
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return Response(cached_payload, status=status.HTTP_200_OK)

        project = getattr(request, "project", None)
        try:
            queryset = GetRoomMessagesHistoryUseCase().execute(
                room_uuid=room_uuid,
                project=project,
            )
        except RoomNotFoundError:
            return Response(
                {"detail": "Room not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except RoomStillActiveError:
            return Response(
                {
                    "detail": (
                        "Room history is only available for closed rooms. "
                        "Close the room before requesting its history."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        page = self.paginate_queryset(queryset)

        reply_index_map = BuildReplyIndexMapUseCase().execute(page)

        reply_index_core_map = {}
        project_uuid = self._resolve_project_uuid(request, room_uuid)
        if is_reply_core_fallback_active(project_uuid):
            reply_index_core_map = BuildReplyIndexCoreMapUseCase().execute(
                page, reply_index_map, room_uuid
            )

        serializer = self.get_serializer(
            page,
            many=True,
            context={
                "reply_index_map": reply_index_map,
                "reply_index_core_map": reply_index_core_map,
            },
        )
        paginated_response = self.get_paginated_response(serializer.data)

        cache.set(
            cache_key,
            paginated_response.data,
            settings.ROOM_HISTORY_CACHE_TTL,
        )

        return paginated_response
