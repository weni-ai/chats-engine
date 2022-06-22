import json

from asgiref.sync import async_to_sync

from django.db.models.signals import post_save
from django.dispatch import receiver

from channels.layers import get_channel_layer

from chats.apps.rooms.models import Room


@receiver(post_save, sender=Room)
def send_websocket_room_notification(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"sector_{instance.sector.pk}",
        {"type": "agent_join_room", "message": json.dumps(instance)},
    )

    async_to_sync(channel_layer.group_send)(
        f"room_notification_{instance.pk}",
        {"type": "room_changed", "message": json.dumps(instance)},
    )
