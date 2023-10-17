import json
import time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from sentry_sdk import capture_exception


def send_channels_group(
    group_name: str,
    call_type: str,
    content: str,
    action: str,
    retry=settings.WS_MESSAGE_RETRIES,
):
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
        if retry > 0:
            time.sleep(settings.WEBSOCKET_RETRY_SLEEP)
            return send_channels_group(
                group_name, call_type, content, action, retry - 1
            )
        capture_exception(err)
