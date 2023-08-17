from django.conf import settings

from chats.apps.event_driven.base_app import EventDrivenAPP


class FlowsQueueMixin:
    base_queue_exchange = settings.FLOWS_QUEUE_EXCHANGE

    def create_queue(self, uuid: str, name: str, sector_uuid: str):
        body = {"sector_uuid": sector_uuid, "uuid": uuid, "name": name}
        EventDrivenAPP().backend.basic_publish(
            content=body, exchange=self.base_queue_exchange, routing_key="create"
        )

    def update_queue(self, uuid: str, name: str, sector_uuid: str):
        body = {"sector_uuid": sector_uuid, "uuid": uuid, "name": name}
        EventDrivenAPP().backend.basic_publish(
            content=body, exchange=self.base_queue_exchange, routing_key="update"
        )

    def destroy_queue(self, uuid: str, sector_uuid: str):
        body = {"sector_uuid": sector_uuid, "uuid": uuid}
        EventDrivenAPP().backend.basic_publish(
            content=body, exchange=self.base_queue_exchange, routing_key="delete"
        )

    def request_queue(self, action, content):
        """
        Generic function to handle Queue actions
        """
        EventDrivenAPP().backend.basic_publish(
            content=content,
            exchange=self.base_queue_exchange,
            routing_key=action,
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
        )


class FlowsEDAClient(FlowsQueueMixin, FlowsTicketerMixin):
    pass
