import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases.permission_creation import (
    ProjectPermissionDTO,
    ProjectPermissionCreationUseCase,
)


class ProjectPermissionConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
        consumer_name="ProjectPermissionConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(
            f"[ProjectPermissionConsumer] - Consuming a message. Body: {message.body}"
        )
        body = JSONParser.parse(message.body)

        project_permission_dto = ProjectPermissionDTO(
            uuid=body.get("uuid"),
            project=body.get("project"),
            user=body.get("user"),
            role=body.get("role"),
        )
        project_permission = ProjectPermissionCreationUseCase(config=body)

        if body.get("action") == "delete":
            project_permission.delete_permission(project_permission_dto)
        elif body.get("action") == "create" or body.get("action") == "update":
            project_permission.create_permission(project_permission_dto)

        channel.basic_ack(message.delivery_tag)
