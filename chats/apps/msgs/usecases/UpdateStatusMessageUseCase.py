from django.conf import settings
from django.db import models

from chats.apps.msgs.models import ChatMessageReplyIndex, Message, MessageMedia
from chats.utils.websockets import send_channels_group


class MessageStatusNotifier:
    @classmethod
    def notify_status_update(cls, message_uuid, message_status, permission_pk):
        send_channels_group(
            group_name=f"permission_{permission_pk}",
            call_type="notify",
            content={"uuid": str(message_uuid), "status": message_status},
            action="message.status_update",
        )

    @classmethod
    def notify_for_message(cls, message, message_status):
        if message and message.room and message.room.user:
            project = message.room.project
            if project:
                permission = message.room.user.project_permissions.filter(
                    project=project
                ).first()
                if permission:
                    cls.notify_status_update(
                        message.uuid, message_status, permission.pk
                    )
                    return True
        return False


class UpdateStatusMessageUseCase:
    def update_status_message(self, message_id, message_status):
        try:
            reply_index = ChatMessageReplyIndex.objects.get(external_id=message_id)
            message = reply_index.message

            project_uuid = str(message.room.project.uuid)
            if project_uuid not in settings.MESSAGE_STATUS_UPDATE_ENABLED_PROJECTS:
                return

            message.status = message_status
            message.save(update_fields=["status"])
            MessageStatusNotifier.notify_for_message(message, message_status)

        except ChatMessageReplyIndex.DoesNotExist:
            print(
                f"Message with external_id {message_id} not found in ChatMessageReplyIndex"
            )
