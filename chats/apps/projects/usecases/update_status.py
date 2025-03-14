from chats.apps.msgs.models import Message, MessageMedia
from django.db import transaction


class UpdateStatusMessageUseCase:

    def update_status_message(self, external_id, message_status):
        with transaction.atomic():
            try:
                message = Message.objects.select_for_update().get(external_id=external_id)
                message.status = message_status
                message.save(update_fields=['status'])
                return
            except Message.DoesNotExist:
                try:
                    message_media = MessageMedia.objects.select_for_update().get(external_id=external_id)
                    message_media.message.status = message_status
                    message_media.message.save(update_fields=['status'])
                except MessageMedia.DoesNotExist:
                    return
