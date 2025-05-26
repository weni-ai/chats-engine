from django.db import transaction

from chats.apps.api.utils import create_reply_index
from chats.apps.msgs.models import Message, MessageMedia
from chats.apps.api.utils import create_reply_index


class SetMsgExternalIdUseCase:
    def execute(self, msg_uuid: str, external_id: str):
        with transaction.atomic():
            try:
                message = Message.objects.select_for_update().get(uuid=msg_uuid)
                message.external_id = external_id
                message.save(update_fields=["external_id"])
                create_reply_index(message)
                return
            except Message.DoesNotExist:
                try:
                    message_media = MessageMedia.objects.select_for_update().get(
                        uuid=msg_uuid
                    )
                    message = message_media.message
                    message.external_id = external_id
                    message.save(update_fields=["external_id"])
                    create_reply_index(message)
                except MessageMedia.DoesNotExist:
                    return
            except Exception as e:
                print(f"Error setting external id: {e}")
                raise e
