import json
from dataclasses import dataclass


@dataclass
class RoomDTO:
    uuid: str
    project_uuid: str
    external_id: str
    created_on: str

    def to_json(self):
        return json.dumps(self.__dict__)
