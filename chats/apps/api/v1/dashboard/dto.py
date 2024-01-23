from dataclasses import dataclass

from chats.apps.projects.models import Project, ProjectPermission


@dataclass
class Agent:
    first_name: str = None
    email: str = None
    agent_status: str = None
    closed_rooms: int = None
    opened_rooms: int = None


@dataclass
class Sector:
    name: str = None
    waiting_time: int = None
    response_time: int = None
    interact_time: int = None


@dataclass
class Filters:
    start_date: str = None
    end_date: str = None
    agent: str = None
    sector: str = None
    queue: str = None
    tag: str = None
    is_weni_admin: bool = None
    user_request: ProjectPermission = None
    project: Project = None


@dataclass
class RoomData:
    interact_time: int = None
    response_time: int = None
    waiting_time: int = None


@dataclass
class ClosedRoomData:
    closed_rooms: dict = None


@dataclass
class TransferRoomData:
    transfer_count: int = None


@dataclass
class QueueRoomData:
    queue_rooms: dict = None


@dataclass
class ActiveRoomData:
    active_rooms: int = None
