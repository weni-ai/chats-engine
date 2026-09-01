import json
import logging
import time

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django_redis import get_redis_connection
from rest_framework import exceptions as drf_exceptions

from chats.apps.api.v1.msgs.serializers import MessageSerializer, MessageWSSerializer
from chats.apps.dashboard.tasks import calculate_first_response_time_task
from chats.apps.msgs.exceptions import MessageCreateError
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia
from chats.apps.msgs.validators.agent_message_create import (
    first_serializer_error,
    map_save_validation_error,
    validate_agent_can_create_message,
)
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)

REQUEST_ID_PENDING_MARKER = "pending"


def _request_id_cache_key(user, request_id: str) -> str:
    return f"agent_message_create:{user.pk}:{request_id}"


def _get_redis_connection_safe():
    try:
        return get_redis_connection()
    except Exception:
        return None


def _decode_redis_value(value):
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def _claim_request_id(user, request_id: str) -> bool:
    """SET NX pending. Returns True when this request won the claim.

    Fail-open: if Redis is unavailable, treat as claimed so creation proceeds.
    """
    redis_conn = _get_redis_connection_safe()
    if redis_conn is None:
        return True

    try:
        was_set = redis_conn.set(
            _request_id_cache_key(user, request_id),
            REQUEST_ID_PENDING_MARKER,
            nx=True,
            ex=settings.AGENT_MESSAGE_CREATE_REQUEST_ID_CACHE_TTL,
        )
        return bool(was_set)
    except Exception:
        logger.warning("Redis unavailable for request_id claim", exc_info=True)
        return True


def _get_request_id_value(user, request_id: str):
    redis_conn = _get_redis_connection_safe()
    if redis_conn is None:
        return None

    try:
        return _decode_redis_value(
            redis_conn.get(_request_id_cache_key(user, request_id))
        )
    except Exception:
        return None


def _store_request_id_message(user, request_id: str, message_uuid) -> None:
    redis_conn = _get_redis_connection_safe()
    if redis_conn is None:
        return

    try:
        redis_conn.set(
            _request_id_cache_key(user, request_id),
            str(message_uuid),
            ex=settings.AGENT_MESSAGE_CREATE_REQUEST_ID_CACHE_TTL,
        )
    except Exception:
        logger.warning("Failed to store request_id in Redis", exc_info=True)


def _release_request_id(user, request_id: str) -> None:
    redis_conn = _get_redis_connection_safe()
    if redis_conn is None:
        return

    try:
        redis_conn.delete(_request_id_cache_key(user, request_id))
    except Exception:
        pass


def _resolve_existing_message(user, request_id: str) -> ChatMessage:
    value = _get_request_id_value(user, request_id)

    if value and value != REQUEST_ID_PENDING_MARKER:
        message = ChatMessage.objects.filter(uuid=value).first()
        if message is not None:
            return message

    for _attempt in range(settings.AGENT_MESSAGE_CREATE_REQUEST_ID_POLL_ATTEMPTS):
        time.sleep(settings.AGENT_MESSAGE_CREATE_REQUEST_ID_POLL_INTERVAL_SECONDS)
        value = _get_request_id_value(user, request_id)
        if value and value != REQUEST_ID_PENDING_MARKER:
            message = ChatMessage.objects.filter(uuid=value).first()
            if message is not None:
                return message

    raise MessageCreateError(
        "duplicate_in_progress",
        _("A message with this request_id is already being created"),
    )


class CreateAgentMessageUseCase:
    def execute(self, user, data: dict) -> ChatMessage:
        request_id = data.get("request_id")
        claimed = False

        if request_id:
            claimed = _claim_request_id(user, request_id)
            if not claimed:
                return _resolve_existing_message(user, request_id)

        try:
            message = self._create_message(user, data)
        except Exception:
            if request_id and claimed:
                _release_request_id(user, request_id)
            raise

        if request_id and claimed:
            _store_request_id_message(user, request_id, message.uuid)

        return message

    def _create_message(self, user, data: dict) -> ChatMessage:
        room_uuid = data.get("room")
        if not room_uuid:
            raise MessageCreateError("validation_error", _("Room is required"))

        room = (
            Room.objects.filter(uuid=room_uuid)
            .select_related("queue__sector__project")
            .first()
        )
        if room is None:
            raise MessageCreateError("room_not_found", _("Room not found"))

        validate_agent_can_create_message(user, room)

        serializer_data = {
            key: data[key]
            for key in ("room", "text", "metadata", "ai_text_improvement")
            if key in data
        }
        serializer_data["room"] = str(room.uuid)

        serializer = MessageSerializer(data=serializer_data)
        if not serializer.is_valid():
            raise MessageCreateError(
                "validation_error",
                first_serializer_error(serializer.errors),
                details=serializer.errors,
            )

        try:
            with transaction.atomic():
                message = serializer.save(user=user)
                PostCreateAgentMessageUseCase().execute(message)
        except drf_exceptions.ValidationError as error:
            raise map_save_validation_error(error) from error
        except drf_exceptions.APIException as error:
            detail = str(error.detail)
            if "waiting for contact" in detail.lower():
                raise MessageCreateError("room_waiting", detail) from error
            raise MessageCreateError("validation_error", detail) from error

        return message


class PostCreateAgentMessageUseCase:
    def execute(self, message: ChatMessage, *, is_media_instance: bool = False) -> None:
        message.notify_room("create", True)

        has_content = message.text or is_media_instance or message.medias.exists()
        if has_content:
            message.room.update_last_message(
                message=message,
                user=message.user,
            )

        room = Room.objects.get(pk=message.room_id)
        if message.user and room.first_user_assigned_at:
            try:
                metric = room.metric
                if metric.first_response_time is None:
                    calculate_first_response_time_task.delay(str(room.uuid))
            except ObjectDoesNotExist:
                calculate_first_response_time_task.delay(str(room.uuid))

    def execute_from_serializer_instance(self, instance) -> None:
        is_media_instance = isinstance(instance, MessageMedia)
        message = instance.message if is_media_instance else instance
        self.execute(message, is_media_instance=is_media_instance)


class SerializeMessageForWsUseCase:
    def execute(self, message: ChatMessage) -> dict:
        return json.loads(
            json.dumps(MessageWSSerializer(message).data, cls=DjangoJSONEncoder)
        )
