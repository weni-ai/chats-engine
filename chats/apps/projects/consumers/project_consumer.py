import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import pyamqp_call_dlx_when_error
from chats.apps.event_driven.consumers import EDAConsumer
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases.project_creation import (
    ProjectCreationDTO,
    ProjectCreationUseCase,
)
from chats.apps.projects.usecases.sector_setup_handler import SectorSetupHandlerUseCase


# TODO: Remove consumer dependency on amqp package
class ProjectConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(f"[ProjectConsumer] - Consuming a message. Body: {message.body}")
        body = JSONParser.parse(message.body)

        project_dto = ProjectCreationDTO(
            uuid=body.get("uuid"),
            name=body.get("name"),
            is_template=body.get("is_template"),
            user_email=body.get("user_email"),
            date_format=body.get("date_format"),
            template_type_uuid=body.get("template_type_uuid"),
            timezone=body.get("timezone"),
            authorizations=body.get("authorizations"),
        )

        sector_setup_handler = SectorSetupHandlerUseCase()

        project_creation = ProjectCreationUseCase(sector_setup_handler)
        project_creation.create_project(project_dto)

        channel.basic_ack(message.delivery_tag)
