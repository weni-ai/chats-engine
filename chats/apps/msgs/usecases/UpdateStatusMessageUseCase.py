from collections import deque

from django.conf import settings

from chats.apps.msgs.models import ChatMessageReplyIndex, Message
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
    READ_STATUSES = ["READ", "V"]
    DELIVERED_STATUSES = ["DELIVERED", "D"]

    def __init__(self):
        self._msgs = deque()

    def _drain_queue(self):
        msgs_to_process = []
        while len(self._msgs) > 0:
            try:
                msgs_to_process.append(self._msgs.popleft())
            except IndexError:
                break
        return msgs_to_process

    def _is_valid_msg_data(self, msg_data):
        return msg_data and isinstance(msg_data, dict) and msg_data.get("message_id")

    def _apply_status_update(self, message, status):
        update_fields = set()
        if status in self.READ_STATUSES and not message.is_read:
            message.is_read = "read"
            update_fields.add("is_read")
        if status in self.DELIVERED_STATUSES and not message.is_delivered:
            message.is_delivered = "delivered"
            update_fields.add("is_delivered")
        return update_fields

    def _process_single_message(self, msg_data):
        try:
            reply_index = ChatMessageReplyIndex.objects.get(external_id=msg_data["message_id"])
            message = reply_index.message

            if not message.room or not message.room.project:
                return None, None

            status = (msg_data["message_status"] or "").upper()
            update_fields = self._apply_status_update(message, status)

            if update_fields:
                message._pending_status = msg_data["message_status"]
                return message, update_fields
        except ChatMessageReplyIndex.DoesNotExist:
            pass
        except Exception as error:
            print(f"[UpdateStatusMessageUseCase] - Error processing message {msg_data.get('message_id')}: {error}")
        return None, None

    def _group_messages_by_fields(self, messages_to_update, message_update_fields):
        fields_to_messages = {}
        for message in messages_to_update:
            fields_key = tuple(sorted(message_update_fields[message.uuid]))
            if fields_key not in fields_to_messages:
                fields_to_messages[fields_key] = []
            fields_to_messages[fields_key].append(message)
        return fields_to_messages

    def _notify_messages(self, messages_to_update):
        for message in messages_to_update:
            if hasattr(message, "_pending_status"):
                try:
                    MessageStatusNotifier.notify_for_message(message, message._pending_status)
                except Exception as error:
                    print(f"[UpdateStatusMessageUseCase] - Notification failed for message {message.uuid}: {error}")

    def _bulk_create(self):
        msgs_to_process = self._drain_queue()
        if not msgs_to_process:
            return

        print(f"[UpdateStatusMessageUseCase] - Processing bulk update of {len(msgs_to_process)} messages")

        messages_to_update = []
        message_update_fields = {}

        for msg_data in msgs_to_process:
            if not self._is_valid_msg_data(msg_data):
                continue
            message, update_fields = self._process_single_message(msg_data)
            if message and update_fields:
                messages_to_update.append(message)
                message_update_fields[message.uuid] = update_fields

        if messages_to_update:
            fields_to_messages = self._group_messages_by_fields(messages_to_update, message_update_fields)
            for fields, messages in fields_to_messages.items():
                Message.objects.bulk_update(messages, list(fields))
            self._notify_messages(messages_to_update)

        print(f"[UpdateStatusMessageUseCase] - Bulk update completed for {len(messages_to_update)} messages")

    def update_status_message(self, message_id, message_status):
        self._msgs.append({"message_id": message_id, "message_status": message_status})
        if len(self._msgs) >= getattr(settings, "MESSAGE_BULK_SIZE", 100):
            self._bulk_create()
