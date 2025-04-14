from django.db import transaction

from chats.apps.msgs.models import Message, MessageMedia


class SetMsgExternalIdUseCase:
    def execute(self, msg_uuid: str, external_id: str):
        with transaction.atomic():
            try:
                message = Message.objects.select_for_update().get(uuid=msg_uuid)
                message.external_id = external_id
                message.save(update_fields=["external_id"])
                return
            except Message.DoesNotExist:
                try:
                    message_media = MessageMedia.objects.select_for_update().get(
                        uuid=msg_uuid
                    )
                    message_media.message.external_id = external_id
                    message_media.save(update_fields=["external_id"])
                except MessageMedia.DoesNotExist:
                    return
            except Exception as e:
                print(f"Error setting external id: {e}")
                raise e
