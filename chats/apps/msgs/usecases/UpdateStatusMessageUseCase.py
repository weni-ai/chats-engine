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
    def __init__(self):
        self._msgs = deque()

    def _bulk_create(self):
        msgs_to_process = []
        while len(self._msgs) > 0:
            try:
                msg = self._msgs.popleft()
                msgs_to_process.append(msg)
            except IndexError:
                break

        if not msgs_to_process:
            return

        print(
            f"[UpdateStatusMessageUseCase] - Processing bulk update of {len(msgs_to_process)} messages"
        )

        messages_to_update = []
        message_update_fields = {}

        for msg_data in msgs_to_process:
            if not msg_data or not isinstance(msg_data, dict):
                continue
            if not msg_data.get("message_id"):
                continue
            try:
                reply_index = ChatMessageReplyIndex.objects.get(
                    external_id=msg_data["message_id"]
                )
                message = reply_index.message

                if not message.room or not message.room.project:
                    continue

                updated = False
                update_fields_for_this_message = set()

                if msg_data["message_status"] in ["read", "V"]:
                    if not message.is_read:
                        message.is_read = "read"
                        update_fields_for_this_message.add("is_read")
                        updated = True

                if msg_data["message_status"] in ["delivered", "D"]:
                    if not message.is_delivered:
                        message.is_delivered = "delivered"
                        update_fields_for_this_message.add("is_delivered")
                        updated = True

                if updated:
                    messages_to_update.append(message)
                    message._pending_status = msg_data["message_status"]
                    message_update_fields[message.uuid] = update_fields_for_this_message

            except ChatMessageReplyIndex.DoesNotExist:
                continue
            except Exception as error:
                print(
                    f"[UpdateStatusMessageUseCase] - Error processing message {msg_data.get('message_id')}: {error}"
                )
                continue

        if messages_to_update:
            fields_to_messages = {}
            for message in messages_to_update:
                fields_key = tuple(sorted(message_update_fields[message.uuid]))
                if fields_key not in fields_to_messages:
                    fields_to_messages[fields_key] = []
                fields_to_messages[fields_key].append(message)

            for fields, messages in fields_to_messages.items():
                Message.objects.bulk_update(messages, list(fields))

            for message in messages_to_update:
                if hasattr(message, "_pending_status"):
                    try:
                        MessageStatusNotifier.notify_for_message(
                            message, message._pending_status
                        )
                    except Exception as error:
                        print(
                            f"[UpdateStatusMessageUseCase] - Notification failed for message {message.uuid}: {error}"
                        )
                        continue

        print(
            f"[UpdateStatusMessageUseCase] - Bulk update completed for {len(messages_to_update)} messages"
        )

    def update_status_message(self, message_id, message_status):
        try:
            reply_index = ChatMessageReplyIndex.objects.select_related(
                "message__room__queue__sector__project"  # CORREÇÃO: caminho correto
            ).get(external_id=message_id)
            project_uuid = str(
                reply_index.message.room.queue.sector.project.uuid
            )  # CORREÇÃO: caminho correto

            if project_uuid not in settings.MESSAGE_STATUS_UPDATE_ENABLED_PROJECTS:
                return
        except ChatMessageReplyIndex.DoesNotExist:
            return
        except Exception:
            return

        self._msgs.append({"message_id": message_id, "message_status": message_status})

        if len(self._msgs) >= getattr(settings, "MESSAGE_BULK_SIZE", 100):
            self._bulk_create()
