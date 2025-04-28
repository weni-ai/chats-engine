from django.db import transaction

from chats.apps.msgs.models import Message, MessageMedia


class UpdateStatusMessageUseCase:
    def update_status_message(self, message_id, message_status):
        with transaction.atomic():
            rows_updated = Message.objects.filter(external_id=message_id).update(
                status=message_status
            )

            if rows_updated == 0:
                MessageMedia.objects.filter(external_id=message_id).update(
                    message__status=message_status
                )
