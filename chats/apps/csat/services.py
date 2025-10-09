from abc import ABC, abstractmethod
from uuid import UUID
import logging
from django.conf import settings
from rest_framework import status

from chats.apps.csat.flows.definitions.flow import (
    CSAT_FLOW_DEFINITION_DATA,
    CSAT_FLOW_VERSION,
)
from chats.apps.projects.models.models import Project
from chats.apps.rooms.models import Room
from django.core.exceptions import ValidationError
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.csat.models import (
    CSAT_FLOW_CACHE_KEY,
    CSAT_FLOW_CACHE_TTL,
    CSATFlowProjectConfig,
)
from chats.core.cache import BaseCacheClient
from chats.apps.api.authentication.token import JWTTokenGenerator

logger = logging.getLogger(__name__)


class BaseCSATService(ABC):
    @abstractmethod
    def get_flow_uuid(self, project_uuid: UUID) -> UUID:
        raise NotImplementedError

    @abstractmethod
    def start_csat_flow(self, room: Room) -> None:
        raise NotImplementedError


class CSATFlowService(BaseCSATService):
    def __init__(
        self,
        flows_client: FlowRESTClient,
        cache_client: BaseCacheClient,
        token_generator: JWTTokenGenerator,
    ):
        self.flows_client = flows_client
        self.cache_client = cache_client
        self.token_generator = token_generator

    def get_flow_uuid(self, project_uuid: UUID) -> UUID:
        cache_key = CSAT_FLOW_CACHE_KEY.format(project_uuid=str(project_uuid))

        if cached_flow_uuid := self.cache_client.get(cache_key):
            return UUID(cached_flow_uuid)

        flow_uuid = (
            CSATFlowProjectConfig.objects.filter(project__uuid=project_uuid)
            .values_list("flow_uuid", flat=True)
            .first()
        )

        if not flow_uuid:
            raise ValueError("CSAT flow not found")

        self.cache_client.set(cache_key, str(flow_uuid), CSAT_FLOW_CACHE_TTL)

        return flow_uuid

    def start_csat_flow(self, room: Room) -> None:
        if room.is_active:
            raise ValidationError("Room is active")

        flow_uuid = self.get_flow_uuid(room.project.uuid)
        token = self.token_generator.generate_token(
            {"project": str(room.project.uuid), "room": str(room.uuid)}
        )

        webhook_url = f"{settings.CHATS_BASE_URL}/v1/internal/csat/"

        data = {
            "flow": str(flow_uuid),
            "urns": [room.urn],
            "params": {
                "room": str(room.uuid),
                "token": token,
                "webhook_url": webhook_url,
            },
        }

        return self.flows_client.start_flow(room.project, data)

    def create_csat_flow(self, project: Project):
        version = CSAT_FLOW_VERSION
        definition = CSAT_FLOW_DEFINITION_DATA

        logger.info(
            "[CSAT FLOW SERVICE] Creating / updating CSAT flow for project %s (%s)",
            project.name,
            project.uuid,
        )

        response = self.flows_client.create_flow_or_update_flow(project, definition)

        logger.info(
            "[CSAT FLOW SERVICE] Flow creation / update response status: %s",
            response.status_code,
        )

        if not status.is_success(response.status_code):
            raise Exception(f"Failed to create CSAT flow: {response.content}")

        flow_uuid = response.json().get("uuid")

        logger.info(
            "[CSAT FLOW SERVICE] Flow UUID: %s",
            flow_uuid,
        )

        current_config = CSATFlowProjectConfig.objects.filter(project=project).first()

        logger.info(
            "[CSAT FLOW SERVICE] Saving CSAT flow config for project %s (%s)",
            project.name,
            project.uuid,
        )

        if current_config:
            fields = ["flow_uuid", "version"]
            fields_to_update = []

            for field in fields:
                if getattr(current_config, field) != getattr(flow_uuid, field):
                    setattr(current_config, field, getattr(flow_uuid, field))
                    fields_to_update.append(field)

            if fields_to_update:
                current_config.save(update_fields=fields_to_update)
        else:
            CSATFlowProjectConfig.objects.create(
                project=project, flow_uuid=flow_uuid, version=version
            )

            current_config.flow_uuid = flow_uuid
            current_config.version = version
            current_config.save()

        logger.info(
            "[CSAT FLOW SERVICE] CSAT flow config saved for project %s (%s)",
            project.name,
            project.uuid,
        )
