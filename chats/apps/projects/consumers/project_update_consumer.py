import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.projects.usecases.project_update import (
    ProjectUpdateDTO,
    ProjectUpdateUseCase,
)


class ProjectUpdateConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
        consumer_name="ProjectUpdateConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(f"[ProjectUpdateConsumer] - Consuming a message. Body: {message.body}")
        body = JSONParser.parse(message.body)

        project_dto = ProjectUpdateDTO(
            project_uuid=body.get("project_uuid"),
            user_email=body.get("user_email"),
            name=body.get("name"),
            timezone=body.get("timezone"),
            date_format=body.get("date_format"),
            config=body.get("config"),
        )

        use_case = ProjectUpdateUseCase()
        use_case.update_project(project_dto)

        channel.basic_ack(message.delivery_tag)
