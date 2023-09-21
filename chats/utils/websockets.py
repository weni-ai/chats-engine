import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.serializers.json import DjangoJSONEncoder
from sentry_sdk import capture_exception


def send_channels_group(group_name: str, call_type: str, content: str, action: str):
    """
    helper function that sends data to channels groups
    """
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": call_type,
                "action": action,
                "content": json.dumps(content, cls=DjangoJSONEncoder),
            },
        )
    except Exception as err:
        capture_exception(err)
