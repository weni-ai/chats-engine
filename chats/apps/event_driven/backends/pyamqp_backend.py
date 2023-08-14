import time

import amqp
from django.conf import settings


class PyAMQPConnectionBackend:
    _start_message = "[+] Connection established. Waiting for events"

    def __init__(self, handle_consumers: callable):
        self._handle_consumers = handle_consumers
        self.connection_params = dict(
            host=settings.EDA_BROKER_HOST,
            port=settings.EDA_BROKER_PORT,
            userid=settings.EDA_BROKER_USER,
            password=settings.EDA_BROKER_PASSWORD,
            virtual_host=settings.EDA_VIRTUAL_HOST,
        )

    def _drain_events(self, connection: amqp.connection.Connection):
        while True:
            connection.drain_events()

    def start_consuming(self, connection_params: dict):
        while True:
            try:
                with amqp.Connection(**connection_params) as connection:
                    channel = connection.channel()

                    self._handle_consumers(channel)

                    print(self._start_message)

                    self._drain_events(connection)

            except (
                amqp.exceptions.AMQPError,
                ConnectionRefusedError,
                OSError,
            ) as error:
                print(f"[-] Connection error: {error}")
                print("    [+] Reconnecting in 5 seconds...")
                time.sleep(5)

            except Exception as error:
                # TODO: Handle exceptions with RabbitMQ
                print("error on drain_events:", type(error), error)
                time.sleep(5)
