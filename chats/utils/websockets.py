import json

from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer


def send_channels_group(group_name: str, type: str, content: str, action: str):
    """
    helper function that sends data to channels groups
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": type,
            "action": action,
            "content": json.dumps(content),
        },
    )
