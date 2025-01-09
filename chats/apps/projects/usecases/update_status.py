from chats.apps.msgs.models import Message, MessageMedia


class UpdateStatusMessageUseCase:

    def update_status_message(self, external_id, message_status):
        message = Message.objects.filter(external_id=external_id)
        if not message:
            message = MessageMedia.objects.filter(external_id=external_id)
        message.status = message_status
        message.save()
