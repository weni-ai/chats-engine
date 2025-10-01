from abc import ABC, abstractmethod
from uuid import UUID

from chats.apps.rooms.models import Room
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.csat.models import CSATFlowProjectConfig
from chats.core.cache import BaseCacheClient


CSAT_FLOW_CACHE_KEY = "csat_flow_uuid:{project_uuid}"
CSAT_FLOW_CACHE_TTL = 300  # 5 minutes


class BaseCSATService(ABC):
    @abstractmethod
    def start_csat_flow(self, room: Room) -> None:
        raise NotImplementedError


class CSATFlowService(BaseCSATService):
    def __init__(self, flows_client: FlowRESTClient, cache_client: BaseCacheClient):
        self.flows_client = flows_client
        self.cache_client = cache_client

    def get_flow_uuid(self, project_uuid: UUID) -> UUID:
        cache_key = CSAT_FLOW_CACHE_KEY.format(project_uuid=project_uuid)

        if cached_flow_uuid := self.cache_client.get(cache_key):
            return UUID(cached_flow_uuid)

        flow_uuid = (
            CSATFlowProjectConfig.objects.filter(project_uuid=project_uuid)
            .values_list("flow_uuid", flat=True)
            .first()
        )

        if not flow_uuid:
            raise ValueError("CSAT flow not found")

        self.cache_client.set(cache_key, str(flow_uuid), CSAT_FLOW_CACHE_TTL)

        return flow_uuid
