import amqp
from django.conf import settings
from weni.eda.django.consumers import EDAConsumer as WeniEDAConsumer

from chats.apps.event_driven.consumers import EDAConsumer as ChatsEDAConsumer
from chats.apps.event_driven.consumers import pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases.project_creation import (
    ProjectCreationDTO,
    ProjectCreationUseCase,
)
from chats.apps.projects.usecases.sector_setup_handler import SectorSetupHandlerUseCase


def _build_project_dto(body: dict) -> ProjectCreationDTO:
    return ProjectCreationDTO(
        uuid=body.get("uuid"),
        name=body.get("name"),
        is_template=body.get("is_template"),
        user_email=body.get("user_email"),
        date_format=body.get("date_format"),
        template_type_uuid=body.get("template_type_uuid"),
        timezone=body.get("timezone"),
        authorizations=body.get("authorizations", []),
        org=body.get("organization_uuid"),
    )


# TODO: Remove consumer dependency on amqp package
class OldProjectConsumer(ChatsEDAConsumer):
    # TODO: Remove this consumer once we permanently migrate to Weni EDA
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
        consumer_name="OldProjectConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(f"[OldProjectConsumer] - Consuming a message. Body: {message.body}")
        body = JSONParser.parse(message.body)

        project_dto = _build_project_dto(body)

        sector_setup_handler = SectorSetupHandlerUseCase()

        project_creation = ProjectCreationUseCase(sector_setup_handler)
        project_creation.create_project(project_dto)

        channel.basic_ack(message.delivery_tag)


class WeniEDAProjectConsumer(WeniEDAConsumer):
    """
    Consumer responsible for handling project creation events from the Weni EDA.
    """

    def consume(self, message: amqp.Message):
        """
        Process an incoming project creation message.
        """
        print(f"[WeniEDAProjectConsumer] - Consuming a message. Body: {message.body}")
        body = JSONParser.parse(message.body)

        project_dto = _build_project_dto(body)

        sector_setup_handler = SectorSetupHandlerUseCase()
        project_creation = ProjectCreationUseCase(sector_setup_handler)
        project_creation.create_project(project_dto)

        self.ack()
