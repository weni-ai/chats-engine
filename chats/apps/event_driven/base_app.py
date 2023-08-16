from django.conf import settings
from django.utils.module_loading import import_string

handle_consumers_function = import_string(settings.EDA_CONSUMERS_HANDLE)
connection_backend = import_string(settings.EDA_CONNECTION_BACKEND)


class EventDrivenAPP:
    """Event Driven Application
    Arguments:
    """

    def __init__(self) -> None:
        self.connection_params = dict(
            host=settings.EDA_BROKER_HOST,
            port=settings.EDA_BROKER_PORT,
            userid=settings.EDA_BROKER_USER,
            password=settings.EDA_BROKER_PASSWORD,
            virtual_host=settings.EDA_VIRTUAL_HOST,
        )
        self.backend = connection_backend(
            handle_consumers_function, self.connection_params
        )
