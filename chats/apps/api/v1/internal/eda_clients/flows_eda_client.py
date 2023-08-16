from django.conf import settings

from chats.apps.event_driven.base_app import EventDrivenAPP


class FlowsQueueMixin:
    def __init__(self) -> None:
        self.base_queue_exchange = settings.FLOWS_QUEUE_EXCHANGE

    def create_queue(self, uuid: str, name: str, sector_uuid: str):
        body = {"sector_uuid": sector_uuid, "uuid": uuid, "name": name}
        EventDrivenAPP().backend.basic_publish(
            content=body, exchange=f"{self.base_queue_exchange}.create", routing_key=""
        )

    def update_queue(self, uuid: str, name: str, sector_uuid: str):
        body = {"sector_uuid": sector_uuid, "uuid": uuid, "name": name}
        EventDrivenAPP().backend.basic_publish(
            content=body, exchange=f"{self.base_queue_exchange}.update", routing_key=""
        )

    def destroy_queue(self, uuid: str, sector_uuid: str):
        body = {"sector_uuid": sector_uuid, "uuid": uuid}
        EventDrivenAPP().backend.basic_publish(
            content=body, exchange=f"{self.base_queue_exchange}.delete", routing_key=""
        )

    def request_queue(self, action, content):
        """
        Generic function to handle Queue actions
        """
        EventDrivenAPP().backend.basic_publish(
            content=content,
            exchange=f"{self.base_queue_exchange}.{action}",
            routing_key="",
        )


class FlowsTicketerMixin:
    def __init__(self) -> None:
        self.base_ticketer_exchange = settings.FLOWS_TICKETER_EXCHANGE

    def create_ticketer(self, **kwargs):
        body = {**kwargs, "ticketer_type": settings.FLOWS_TICKETER_TYPE}
        EventDrivenAPP().backend.basic_publish(
            content=body, exchange=f"{self.base_queue_exchange}.delete", routing_key=""
        )

    def request_ticketer(self, action, content):
        """
        Generic function to handle Queue actions
        """
        EventDrivenAPP().backend.basic_publish(
            content=content,
            exchange=f"{self.base_ticketer_exchange}.{action}",
            routing_key="",
        )


class FlowsEDAClient(FlowsQueueMixin, FlowsTicketerMixin):
    pass
