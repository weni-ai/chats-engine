import json
import time

import amqp
from django.conf import settings


class PyAMQPConnectionBackend:
    _start_message = "[+] Connection established. Waiting for events"

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
        routing_key: str,
        content_type: str = "application/json",
    ):
        sent = False
        while not sent:
            try:
                with self._conection(confirm_publish=True) as c:
                    ch = c.channel()
                    ch.basic_publish(
                        amqp.Message(
                            body=json.dumps(content),
                            content_type=content_type,
                            content_encoding="utf-8",
                            properties={"delivery_mode": 2},
                        ),
                        exchange=exchange,
                        routing_key=routing_key,
                    )
                    sent = True
            except Exception as err:
                print(f"{type(err)}: {err}")

                time.sleep(settings.EDA_WAIT_TIME_RETRY)
