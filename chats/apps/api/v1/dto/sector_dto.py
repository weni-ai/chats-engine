from dataclasses import dataclass
from typing import List, Dict
from .queue_dto import QueueDTO


@dataclass
class SectorDTO:
    manager_email: List[str]
    working_hours: Dict[str, str]
    service_limit: int
    tags: List[str]
    name: str
    uuid: str
    queues: List[QueueDTO]


@dataclass
class FeatureVersionDTO:
    project: str
    feature_version: str


def dto_to_dict(dto: SectorDTO) -> Dict:
    return {
        "manager_email": dto.manager_email,
        "working_hours": dto.working_hours,
        "service_limit": dto.service_limit,
        "tags": dto.tags,
        "name": dto.name,
        "uuid": dto.uuid,
        "queues": [
            {"uuid": queue.uuid, "name": queue.name, "agents": queue.agents}
            for queue in dto.queues
        ],
    }
