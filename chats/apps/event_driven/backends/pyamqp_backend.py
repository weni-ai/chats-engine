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
                with amqp.Connection(**self.connection_params) as connection:
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
                time.sleep(5)

            except KeyboardInterrupt:
                print(f"[-] Connection closed: Keyboard Interrupt")
                break

            except Exception as error:
                # TODO: Handle exceptions with RabbitMQ
                print("error on drain_events:", type(error), error)
                time.sleep(5)
