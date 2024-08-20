import amqp
from django.conf import settings

from chats.apps.event_driven.consumers import EDAConsumer, pyamqp_call_dlx_when_error
from chats.apps.event_driven.parsers.json_parser import JSONParser
from chats.apps.api.v1.dto.sector_dto import FeatureVersionDTO
from chats.apps.projects.usecases.delete_integration import DeleteIntegrationUseCase


class DeleteIntegrationConsumer(EDAConsumer):
    @staticmethod
    @pyamqp_call_dlx_when_error(
        default_exchange=settings.CONNECT_DEFAULT_DEAD_LETTER_EXCHANGE,
        routing_key="",
        consumer_name="DeleteIntegrationConsumer",
    )
    def consume(message: amqp.Message):
        channel = message.channel
        print(
            f"[DeleteIntegrationConsumer] - Consuming a message. Body: {message.body}"
        )

        body = JSONParser.parse(message.body)

        feature_version_dto = FeatureVersionDTO(
            project=body.get("project_uuid"),
            feature_version=body.get("feature_version_uuid"),
        )

        delete_integrarion_usecase = DeleteIntegrationUseCase()

        delete_integrarion_usecase.delete(feature_version_dto)

        channel.basic_ack(message.delivery_tag)
