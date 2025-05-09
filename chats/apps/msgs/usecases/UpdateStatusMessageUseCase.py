from django.db import models

from chats.apps.msgs.models import Message, MessageMedia
from chats.utils.websockets import send_channels_group


class MessageStatusNotifier:
    @classmethod
    def notify_status_update(cls, message_uuid, message_status, permission_pk):
        print("chegou no notify_status_update")
        print("--------------------------------")
        print(f"message_uuid: {message_uuid}")
        print(f"message_status: {message_status}")
        print(f"permission_pk: {permission_pk}")
        print("--------------------------------")
        send_channels_group(
            group_name=f"permission_{permission_pk}",
            call_type="notify",
            content={"uuid": str(message_uuid), "status": message_status},
            action="message.status_update",
        )

    @classmethod
    def find_and_notify_for_message(cls, message_id, message_status):
        # Primeiro obtemos apenas a mensagem
        message = Message.objects.filter(
            external_id=message_id, 
            room__is_active=True, 
            room__user__isnull=False
        ).first()
        print("mensagem", message)
        
        if message and message.room and message.room.user:
            # Buscamos diretamente o projeto da sala
            print("chegou no if message and message.room and message.room.user")
            print("--------------------------------")
            project = message.room.project
            print("project", project)
            print("--------------------------------")
            if project:
                # Buscamos a permissão específica para este usuário neste projeto
                print("chegou no if project")
                print("--------------------------------")
                permission = message.room.user.project_permissions.filter(
                    project=project
                ).first()
                print("permission", permission)
                print("--------------------------------")
                if permission:
                    cls.notify_status_update(
                        message.uuid, 
                        message.status, 
                        permission.pk
                    )
                    return True
        return False

    @classmethod
    def find_and_notify_for_media(cls, message_id, message_status):
        print("chegou no find_and_notify_for_media")
        print("--------------------------------")
        print(f"message_id: {message_id}")
        print(f"message_status: {message_status}")
        print("--------------------------------")
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
        print("depois de procurar a media") 
        print("--------------------------------")
        print(f"media_data: {media_data}")
        print("--------------------------------")
        if media_data:
            print("depois de verificar se a media existe")
            print("--------------------------------")
            uuid, permission_pk = media_data
            print("depois de pegar o uuid e o permission_pk")
            print("--------------------------------")
            cls.notify_status_update(uuid, message_status, permission_pk)
            print("depois de notificar o status da media")
            print("--------------------------------")
            return True
        return False


class UpdateStatusMessageUseCase:
    def update_status_message(self, message_id, message_status):
        print("chegou no update_status_message")
        print("--------------------------------")
        print(f"message_id: {message_id}")
        print(f"message_status: {message_status}")
        print("--------------------------------")
        rows_updated = Message.objects.filter(external_id=message_id).update(
            status=message_status
        )
        if rows_updated > 0:
            print("depois de atualizar a mensagem")
            print("--------------------------------")
            print("dado enviado", message_id, message_status)
            print("--------------------------------")
            MessageStatusNotifier.find_and_notify_for_message(
                message_id, message_status
            )
            return

        media_rows_updated = MessageMedia.objects.filter(external_id=message_id).update(
            message__status=message_status
        )       
        if media_rows_updated > 0:
            MessageStatusNotifier.find_and_notify_for_media(message_id, message_status)
