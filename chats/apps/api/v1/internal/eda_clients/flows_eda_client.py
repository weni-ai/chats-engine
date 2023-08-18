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
            routing_key=action,
            headers={"callback_exchange": settings.DEFAULT_DEAD_LETTER_EXCHANGE},
        )


class FlowsTicketerMixin:
    base_ticketer_exchange = settings.FLOWS_TICKETER_EXCHANGE

    def create_ticketer(self, **kwargs):
        body = {**kwargs, "ticketer_type": settings.FLOWS_TICKETER_TYPE}
        EventDrivenAPP().backend.basic_publish(
            content=body, exchange=self.base_queue_exchange, routing_key="create"
        )

    def request_ticketer(self, action, content):
        """
        Generic function to handle Queue actions
        """
        EventDrivenAPP().backend.basic_publish(
            content=content,
            exchange=self.base_ticketer_exchange,
            routing_key=action,
            headers={"callback_exchange": settings.DEFAULT_DEAD_LETTER_EXCHANGE},
        )


class FlowsEDAClient(FlowsQueueMixin, FlowsTicketerMixin):
    pass
