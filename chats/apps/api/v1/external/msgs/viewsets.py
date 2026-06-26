import logging
from functools import cached_property

from django.conf import settings
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, mixins, status, viewsets
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from sentry_sdk import capture_exception
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

from chats.apps.accounts.authentication.drf.authorization import (
    ProjectAdminAuthentication,
    get_token_auth_classes,
)
from chats.apps.accounts.permissions import IsExternalProject
from chats.apps.api.authentication.permissions import InternalAPITokenRequiredPermission
from chats.apps.api.v1.external.msgs.filters import MessageFilter
from chats.apps.api.v1.external.msgs.serializers import (
    MsgFlowSerializer,
    RoomHistoryMessageSerializer,
    RoomHistoryQuerySerializer,
)
from chats.apps.api.v1.external.permissions import IsAdminPermission
from chats.apps.api.v1.external.throttling import (
    ExternalHourRateThrottle,
    ExternalMinuteRateThrottle,
    ExternalRoomHistoryHourRateThrottle,
    ExternalRoomHistoryMinuteRateThrottle,
    ExternalRoomHistorySecondRateThrottle,
    ExternalSecondRateThrottle,
)
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.msgs.exceptions import RoomNotFoundError, RoomStillActiveError
from chats.apps.msgs.models import ChatMessageReplyIndex, Message as ChatMessage
from chats.apps.msgs.usecases.get_room_messages_history import (
    GetRoomMessagesHistoryUseCase,
)
from chats.apps.msgs.utils import extract_wamid_core

logger = logging.getLogger(__name__)


def _is_reply_core_fallback_active(project_uuid: str) -> bool:
    """Wrapper around the WAMID core fallback feature flag.

    Mirrors the safety pattern used elsewhere in the codebase
    (see ``MessageMedia.is_flows_media_url_feature_active``): any failure
    in the feature flag integration is captured but never bubbles up,
    keeping the request on the legacy/exact-match path.
    """

    if not project_uuid:
        return False

    try:
        return is_feature_active_for_attributes(
            settings.REPLY_CORE_FALLBACK_FEATURE_FLAG_KEY,
            {"projectUUID": project_uuid},
        )
    except Exception as e:
        capture_exception(e)
        logger.error(
            "Error checking if reply core fallback feature flag is active: %s", e
        )
        return False


class MessageFlowViewset(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for creating, listing and updating messages via external API.

    Supports both project admin authentication (Bearer token) and module authentication.
    Rate limited: 20/sec, 600/min, 30k/hour.
    """

    swagger_tag = "Integrations"
    queryset = ChatMessage.objects.all()
    serializer_class = MsgFlowSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = MessageFilter
    lookup_field = "uuid"
    throttle_classes = [
        ExternalSecondRateThrottle,  # Máx 20/seg
        ExternalMinuteRateThrottle,  # Máx 600/min
        ExternalHourRateThrottle,  # Máx 30k/hora
    ]

    @cached_property
    def authentication_classes(self):
        return get_token_auth_classes(self.request)

    @cached_property
    def permission_classes(self):
        if self.request.auth and hasattr(self.request.auth, "project"):
            return [IsAdminPermission]
        elif self.request.auth == "INTERNAL":
            return [InternalAPITokenRequiredPermission]
        return [ModuleHasPermission]

    @swagger_auto_schema(auto_schema=None)
    def list(self, request, *args, **kwargs):
        """List messages filtered by room or other criteria."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def create(self, request, *args, **kwargs):
        """Create a new message in a room (incoming or outgoing direction)."""
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def partial_update(self, request, *args, **kwargs):
        """Update message fields (e.g., mark as seen)."""
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        room = validated_data.get("room")
        if (
            self.request.auth
            and hasattr(self.request.auth, "project")
            and room.project_uuid != self.request.auth.project
        ):
            self.permission_denied(
                self.request,
                message="Ticketer token permission failed on room project",
                code=403,
            )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.notify_room("create")
        room = instance.room
        room.on_new_message(
            message=instance,
            contact=instance.contact,
            increment_unread=1,
        )
        if room.user is None and instance.contact:
            room.trigger_default_message()

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.notify_room("update")


class RoomHistoryMessagesPagination(CursorPagination):
    page_size = 100
    max_page_size = 100
    ordering = "created_on"
    cursor_query_param = "cursor"


class RoomHistoryMessagesViewSet(viewsets.GenericViewSet):
    """
    Read-only endpoint that returns the message history of a closed room.

    Authenticated exclusively via project admin Bearer tokens. Internal notes
    are excluded at the database level. Responses are cached per
    ``(room, cursor)`` for ``settings.ROOM_HISTORY_CACHE_TTL`` seconds.
    Rate limited: 5/sec, 100/min, 4000/hour.
    """

    swagger_tag = "Integrations"
    serializer_class = RoomHistoryMessageSerializer
    authentication_classes = [ProjectAdminAuthentication]
    permission_classes = [IsExternalProject]
    throttle_classes = [
        ExternalRoomHistorySecondRateThrottle,
        ExternalRoomHistoryMinuteRateThrottle,
        ExternalRoomHistoryHourRateThrottle,
    ]
    pagination_class = RoomHistoryMessagesPagination

    @staticmethod
    def _cache_key(room_uuid: str, cursor: str) -> str:
        return f"external:room_history:{room_uuid}:{cursor or ''}"

    @staticmethod
    def _build_reply_index_map(messages) -> dict:
        """
        Bulk-fetch ChatMessageReplyIndex rows for every replied-to
        external_id in the page, returning a dict keyed by external_id.
        """
        external_ids = set()
        for msg in messages:
            metadata = msg.metadata if isinstance(msg.metadata, dict) else {}
            context = metadata.get("context")
            if isinstance(context, dict):
                ext_id = context.get("id")
                if ext_id:
                    external_ids.add(ext_id)

        if not external_ids:
            return {}

        return {
            ri.external_id: ri
            for ri in ChatMessageReplyIndex.objects.select_related("message").filter(
                external_id__in=external_ids
            )
        }

    @staticmethod
    def _build_reply_index_core_map(messages, exact_map: dict) -> dict:
        """
        Bulk-fetch ChatMessageReplyIndex rows by stable WAMID core for every
        replied-to id that was *not* resolved by the exact ``external_id``
        lookup. Returns a dict keyed by ``external_id_core`` so callers can
        fall back when Meta sent a different envelope inside ``context.id``.
        """
        unresolved = set()
        for msg in messages:
            metadata = msg.metadata if isinstance(msg.metadata, dict) else {}
            context = metadata.get("context")
            if isinstance(context, dict):
                ext_id = context.get("id")
                if ext_id and ext_id not in exact_map:
                    unresolved.add(ext_id)

        if not unresolved:
            return {}

        cores = {core for core in (extract_wamid_core(eid) for eid in unresolved) if core}
        if not cores:
            return {}

        return {
            ri.external_id_core: ri
            for ri in (
                ChatMessageReplyIndex.objects.select_related("message")
                .filter(external_id_core__in=cores)
                .order_by("created_on")
            )
        }

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

        try:
            queryset = GetRoomMessagesHistoryUseCase().execute(
                room_uuid=room_uuid,
                project=request.auth.project,
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

        reply_index_map = self._build_reply_index_map(page)

        reply_index_core_map = {}
        try:
            project_uuid = str(request.auth.project)
        except AttributeError:
            project_uuid = ""

        if _is_reply_core_fallback_active(project_uuid):
            reply_index_core_map = self._build_reply_index_core_map(
                page, reply_index_map
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
