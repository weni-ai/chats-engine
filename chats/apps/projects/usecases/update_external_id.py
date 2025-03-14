from django.db import transaction

from chats.apps.msgs.models import Message, MessageMedia


class UpdateExternalIdMessageUseCase:

    def update_external_id(self, message_uuid, external_id):
        with transaction.atomic():
            try:
                message = Message.objects.select_for_update().get(uuid=message_uuid)
                message.external_id = external_id
                message.save(update_fields=['external_id'])
                return
            except Message.DoesNotExist:
                try:
                    message_media = MessageMedia.objects.select_for_update().get(uuid=message_uuid)
                    message_media.message.external_id = external_id
                    message_media.save(update_fields=['external_id'])
                except MessageMedia.DoesNotExist:
                    return
