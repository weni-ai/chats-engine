from dataclasses import dataclass, field
from typing import List
from uuid import UUID


@dataclass
class FlowTemplateChannel:
    uuid: str
    name: str = ""
    template_name: str = ""


@dataclass
class FlowTemplate:
    id: str
    name: str
    data: dict


@dataclass
class FlowTemplatesData:
    uuid: UUID
    templates: List[FlowTemplate] = field(default_factory=list)
