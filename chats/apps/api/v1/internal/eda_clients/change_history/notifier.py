from datetime import datetime

from weni.eda.django import AMQConnectionParamsFactory
from weni.eda.eda_publisher import EDAPublisher

from chats.apps.api.v1.internal.eda_clients.change_history.actions import Action
from chats.apps.api.v1.internal.eda_clients.change_history.entities import Entity
from chats.apps.api.v1.internal.eda_clients.change_history.modules import Module


class Notifier:
    EXCHANGE = "change-history.topic"

    @staticmethod
    def notify_change(
        project_uuid: str,
        user_email: str,
        date: datetime,
        action: Action,
        entity: Entity,
        module: Module,
        object_id: str = None,
        object_name: str = None,
        old_value: str = None,
        new_value: str = None,
        user_ip: str = None,
    ):
        body = dict(
            project_uuid=project_uuid,
            user_email=user_email,
            date=str(date),
            action=action.value,
            entity=entity.value,
            module=module.value,
        )

        if old_value is not None:
            body["old_value"] = old_value

        if new_value is not None:
            body["new_value"] = new_value

        if object_id is not None:
            body["object_id"] = object_id

        if object_name is not None:
            body["object_name"] = object_name

        if user_ip is not None:
            body["user_ip"] = user_ip

        EDAPublisher(AMQConnectionParamsFactory).send_message(body, Notifier.EXCHANGE)
