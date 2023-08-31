import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers import JSONParser
from chats.apps.projects.usecases import (
    ProjectCreationDTO,
    ProjectCreationUseCase,
    SectorSetupHandlerUseCase,
)


# TODO: Remove consumer dependency on amqp package
class ProjectConsumer:
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
        )

        sector_setup_handler = SectorSetupHandlerUseCase()

        project_creation = ProjectCreationUseCase(sector_setup_handler)
        project_creation.create_project(project_dto)

        channel.basic_ack(message.delivery_tag)


"""
For the error handling, we reject the message and publish a new message to a error queue,
this way it would be possible to pass more information about the error.
We could send a 'callback_exchange' field on the message body or,
then we're able to send the error to the correct exchange
e.g.
Connect calls the chats project consumer
{project_data..., callback_exchange="connect.project.dlx"}
the error will be delivered to the 'connect.project.dlx' exchange

flows calls the chats project consumer
{project_data..., callback_exchange="flows.project.dlx"}
the error will be delivered to the 'flows.project.dlx' exchange
"""
