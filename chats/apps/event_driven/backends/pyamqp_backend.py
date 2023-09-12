import json
import time

import amqp
from django.conf import settings


def basic_publish(
    channel: amqp.Channel,
    content: dict,
    exchange: str,
    content_type: str = "application/octet-stream",
    properties: dict = {"delivery_mode": 2},
    headers: dict = {},
    content_encoding: str = None,
) -> None:
    channel.basic_publish(
        amqp.Message(
            body=bytes(json.dumps(content), "utf-8"),
            content_type=content_type,
            content_encoding=content_encoding,
            properties=properties,
            application_headers=headers,
        ),
        exchange=exchange,
    )


class PyAMQPConnectionBackend:
    _start_message = (
        "[+] Connection established. Waiting for events. To exit press CTRL+C"
    )

    def __init__(self, handle_consumers: callable, connection_params: dict):
        self._handle_consumers = handle_consumers
        self.connection_params = connection_params

    def _drain_events(self, connection: amqp.connection.Connection):
        while True:
            connection.drain_events()

    def _conection(self, **kwargs) -> amqp.Connection:
        return amqp.Connection(**self.connection_params, **kwargs)

    def start_consuming(self):
        while True:
            try:
                with self._conection() as connection:
                    channel = connection.channel()

                    self._handle_consumers(channel)

                    print(self._start_message)

                    self._drain_events(connection)

            except (
                *amqp.Connection.connection_errors,
                amqp.exceptions.AMQPError,
                ConnectionRefusedError,
            ) as error:
                print(f"[-] Connection error: {error}")
                print("    [+] Reconnecting in 5 seconds...")
                time.sleep(settings.EDA_WAIT_TIME_RETRY)

            except KeyboardInterrupt:
                print("[-] Connection closed: Keyboard Interrupt")
                break

            except Exception as error:
                # TODO: Handle exceptions with RabbitMQ
                print("error on drain_events:", type(error), error)
                time.sleep(settings.EDA_WAIT_TIME_RETRY)

    def basic_publish(
        self,
        content: dict,
        exchange: str,
        content_type: str = "application/octet-stream",
        headers: dict = {},
    ):
        sent = False
        while not sent:
            try:
                with self._conection(confirm_publish=True) as c:
                    basic_publish(
                        channel=c.channel(),
                        content=content,
                        content_type=content_type,
                        properties={"delivery_mode": 2},
                        exchange=exchange,
                        headers=headers,
                    )
                    sent = True
            except Exception as err:
                print(f"{type(err)}: {err}")

                time.sleep(settings.EDA_WAIT_TIME_RETRY)
