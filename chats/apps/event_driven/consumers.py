from chats.apps.event_driven.backends.pyamqp_backend import basic_publish
from chats.apps.event_driven.parsers.exceptions import ParseError
from chats.apps.projects.usecases.exceptions import (
    InvalidProjectData,
    InvalidTemplateTypeData,
)


def pyamqp_call_dlx_when_error(routing_key: str, default_exchange: str):
    def decorator(consumer):
        def consumer_wrapper(*args, **kw):
            message = args[0]
            channel = message.channel
            try:
                return consumer(*args, **kw)
            except (
                ParseError,
                InvalidTemplateTypeData,
                InvalidProjectData,
                TypeError,
                AttributeError,
            ) as err:
                channel.basic_reject(message.delivery_tag, requeue=False)
                callback_body = {
                    "original_message": message.body.decode("utf-8"),
                    "error_type": str(type(err)),
                    "error_message": str(err),
                }
                exchange = message.headers.get("callback_exchange") or default_exchange
                basic_publish(
                    channel=channel,
                    content=callback_body,
                    properties={"delivery_mode": 2},
                    exchange=exchange,
                )

        return consumer_wrapper

    return decorator
