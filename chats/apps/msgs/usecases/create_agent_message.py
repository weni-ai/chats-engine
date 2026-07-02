from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.translation import gettext_lazy as _
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


class CreateAgentMessageUseCase:
    def execute(self, user, data: dict) -> ChatMessage:
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
        return dict(MessageWSSerializer(message).data)
