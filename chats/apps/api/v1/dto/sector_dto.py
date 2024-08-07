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
