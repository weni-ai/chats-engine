from dataclasses import dataclass
from typing import List, Dict


@dataclass
class RoomDTO:
    project_uuid: str
    external_id: str
    created_on: str
