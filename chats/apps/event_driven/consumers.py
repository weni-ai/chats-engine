from abc import ABC, abstractmethod

import amqp
from sentry_sdk import capture_exception

from chats.apps.event_driven.backends.pyamqp_backend import basic_publish

from .signals import message_finished, message_started


def pyamqp_call_dlx_when_error(
    routing_key: str, default_exchange: str, consumer_name: str
):
    def decorator(consumer):
        def consumer_wrapper(*args, **kw):
            message = args[0]
            channel = message.channel
            try:
                return consumer(*args, **kw)
            except Exception as error:
                capture_exception(error)
                try:
                    channel.basic_reject(message.delivery_tag, requeue=False)
                except Exception as reject_err:
                    print(f"[{consumer_name}] - Failed to reject message: {reject_err}")
                    return

                print(f"[{consumer_name}] - Message rejected by: {error}")

                headers = getattr(message, "headers", {}) or {}
                error_count = headers.get("x-error-count", 0)

                if error_count >= 3:
                    print(
                        f"[{consumer_name}] - Max error retries reached, dropping message"
                    )
                    return

                try:
                    callback_body = {
                        "original_message": message.body.decode("utf-8"),
                        "error_type": str(type(error)),
                        "error_message": str(error),
                    }
                    exchange = headers.get("callback_exchange") or default_exchange

                    new_headers = dict(headers)
                    new_headers["x-error-count"] = error_count + 1

                    basic_publish(
                        channel=channel,
                        content=callback_body,
                        properties={"delivery_mode": 2},
                        exchange=exchange,
                        headers=new_headers,
                    )
                except Exception as publish_err:
                    print(
                        f"[{consumer_name}] - Failed to publish to DLX: {publish_err}"
                    )

        return consumer_wrapper

    return decorator


class EDAConsumer(ABC):  # pragma: no cover
    def handle(self, message: amqp.Message):
        message_started.send(sender=self)
        try:
            self.consume(message)
        finally:
            message_finished.send(sender=self)

    @abstractmethod
    def consume(self, message: amqp.Message):
        pass
