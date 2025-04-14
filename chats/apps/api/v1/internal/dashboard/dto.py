from dataclasses import dataclass
from typing import List

from chats.apps.projects.models import Project, ProjectPermission


@dataclass
class Filters:
    start_date: str = None
    end_date: str = None
    agent: str = None
    sector: List = None
    queue: str = None
    tag: str = None
    is_weni_admin: bool = None
    user_request: ProjectPermission = None
    project: Project = None
