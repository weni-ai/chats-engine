from abc import ABC, abstractmethod
from uuid import UUID

from django.conf import settings

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
