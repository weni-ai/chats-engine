from dataclasses import dataclass

from chats.apps.projects.models import ProjectPermission


@dataclass
class Agent:
    first_name: str = None
    email: str = None
    agent_status: str = None
    closed_rooms: int = None
    opened_rooms: int = None


@dataclass
class Filters:
    start_date: str = None
    end_date: str = None
    agent: str = None
    sector: str = None
    tag: str = None
    is_weni_admin: bool = None
    user_request: ProjectPermission = None
    project: str = None


@dataclass
class ClosedRoomData:
    closed_rooms: dict = None


@dataclass
class TransferRoomData:
    transfer_count: dict = None


@dataclass
class QueueRoomData:
    queue_rooms: dict = None
