import amqp

from chats.apps.event_driven.parsers import JSONParser
from chats.apps.projects.usecases import (
    ProjectCreationDTO,
    ProjectCreationUseCase,
    SectorSetupHandlerUseCase,
)


class ProjectConsumer:
    @staticmethod
    def consume(message: amqp.Message):
        body = JSONParser.parse(message.body)
        print(f"[ProjectConsumer] - Consuming a message. Body: {body}")

        project_dto = ProjectCreationDTO(
            uuid=body.get("uuid"),
            name=body.get("name"),
            is_template=body.get("is_template"),
            user_email=body.get("user_email"),
            date_format=body.get("date_format"),
            template_type_uuid=body.get("template_type_uuid"),
            timezone=body.get("timezone"),
        )

        sector_setup_handler = SectorSetupHandlerUseCase()

        project_creation = ProjectCreationUseCase(sector_setup_handler)
        project_creation.create_project(project_dto)

        message.channel.basic_ack(message.delivery_tag)
