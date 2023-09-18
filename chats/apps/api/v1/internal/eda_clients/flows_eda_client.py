from django.conf import settings

from chats.apps.event_driven.base_app import EventDrivenAPP


class FlowsQueueMixin:
    base_queue_exchange = settings.FLOWS_QUEUE_EXCHANGE

    def request_queue(self, action, content):
        """
        Generic function to handle Queue actions
        """
        EventDrivenAPP().backend.basic_publish(
            content=content,
            exchange=self.base_queue_exchange,
            headers={"callback_exchange": settings.DEFAULT_DEAD_LETTER_EXCHANGE},
        )


class FlowsTicketerMixin:
    base_ticketer_exchange = settings.FLOWS_TICKETER_EXCHANGE

    def request_ticketer(self, content):
        """
        Generic function to handle Queue actions
        """
        EventDrivenAPP().backend.basic_publish(
            content=content,
            exchange=self.base_ticketer_exchange,
            headers={"callback_exchange": settings.DEFAULT_DEAD_LETTER_EXCHANGE},
        )


class FlowsEDAClient(FlowsQueueMixin, FlowsTicketerMixin):
    pass
