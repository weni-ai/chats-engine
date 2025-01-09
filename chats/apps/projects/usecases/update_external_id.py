from chats.apps.msgs.models import Message, MessageMedia


class UpdateExternalIdMessageUseCase:

    def update_external_id(self, message_uuid, external_id):
        message = Message.objects.filter(uuid=message_uuid)
        if not message:
            message = MessageMedia.objects.filter(uuid=message_uuid)
        message.external_id = external_id
        message.save()
