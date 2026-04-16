import logging

from chats.apps.ai_features.improve_user_message.services import (
    ImproveUserMessageService,
)
from chats.apps.ai_features.integrations.factories import AIModelPlatformClientFactory
from chats.apps.projects.models import Project

logger = logging.getLogger(__name__)


class ImproveUserMessageUseCase:
    def __init__(
        self,
        integration_client_factory: type[AIModelPlatformClientFactory] = AIModelPlatformClientFactory,
    ):
        self.integration_client_factory = integration_client_factory

    def execute(self, text: str, improvement_type: str, project: Project) -> str:
        integration_client_class = self.integration_client_factory.get_client_class(
            "bedrock"
        )
        service = ImproveUserMessageService(integration_client_class)

        return service.generate_improved_message(
            user_message_text=text,
            improvement_type=improvement_type,
            project=project,
        )
