from dataclasses import dataclass
from typing import Dict, List

from .queue_dto import QueueDTO


@dataclass
class SectorDTO:
    working_hours: Dict[str, str]
    service_limit: int
    tags: List[str]
    name: str
    queues: List[QueueDTO]


@dataclass
class FeatureVersionDTO:
    project: str
    feature_version: str


def dto_to_dict(dto: SectorDTO) -> Dict:
    return {
        "name": dto.name,
        "tags": dto.tags,
        "queues": [{"uuid": queue.uuid, "name": queue.name} for queue in dto.queues],
    }
