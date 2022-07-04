import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from chats.apps.msgs.models import Message as ChatMessage


@receiver(post_save, sender=ChatMessage)
def send_websocket_message_notification(sender, instance, created, **kwargs):
    pass
    # if created:
    #     channel_layer = get_channel_layer()
    #     async_to_sync(channel_layer.group_send)(
    #         f"service_{instance.room.pk}",
    #         {"type": "room_messages", "message": json.dumps(instance)},
    #     )
