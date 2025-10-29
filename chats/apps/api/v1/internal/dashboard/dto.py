from dataclasses import dataclass
from chats.apps.projects.models import Project, ProjectPermission
from typing import List, Optional


@dataclass
class Filters:
    start_date: str = None
    end_date: str = None
    agent: str = None
    sector: List = None
    queue: str = None
    queues: List = None
    tag: str = None
    tags: List = None
    is_weni_admin: bool = None
    user_request: ProjectPermission = None
    project: Project = None
    ordering: str = None


@dataclass(frozen=True)
class CSATScoreGeneral:
    rooms: int
    reviews: int
    avg_rating: Optional[float] = None


@dataclass
class CSATRatingCount:
    rating: int
    count: int
    percentage: float


@dataclass
class CSATRatings:
    ratings: List[CSATRatingCount]
