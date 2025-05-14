from django.db import models

from chats.apps.msgs.models import Message, MessageMedia
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
    def find_and_notify_for_message(cls, message_id, message_status):
        message = Message.objects.filter(
            external_id=message_id, room__is_active=True, room__user__isnull=False
        ).first()

        if message and message.room and message.room.user:
            project = message.room.project
            if project:
                permission = message.room.user.project_permissions.filter(
                    project=project
                ).first()
                if permission:
                    cls.notify_status_update(
                        message.uuid, message.status, permission.pk
                    )
                    return True
        return False

    @classmethod
    def find_and_notify_for_media(cls, message_id, message_status):
        media_data = (
            MessageMedia.objects.filter(
                external_id=message_id,
                message__room__is_active=True,
                message__room__user__isnull=False,
            )
            .values_list(
                "message__uuid", "message__room__user__project_permissions__pk"
            )
            .filter(
                message__room__user__project_permissions__project=models.F(
                    "message__room__queue__sector__project"
                )
            )
            .first()
        )
        if media_data:
            uuid, permission_pk = media_data
            cls.notify_status_update(uuid, message_status, permission_pk)
            return True
        return False


class UpdateStatusMessageUseCase:
    def update_status_message(self, message_id, message_status):
        rows_updated = Message.objects.filter(external_id=message_id).update(
            status=message_status
        )
        if rows_updated > 0:
            MessageStatusNotifier.find_and_notify_for_message(
                message_id, message_status
            )
            return

        media_rows_updated = MessageMedia.objects.filter(external_id=message_id).update(
            message__status=message_status
        )
        if media_rows_updated > 0:
            MessageStatusNotifier.find_and_notify_for_media(message_id, message_status)
