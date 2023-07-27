import amqp


class PyAMQPConnectionBackend:
    _start_message = "Waiting Events"

    def __init__(self, handle_consumers: callable):
        self._handle_consumers = handle_consumers
