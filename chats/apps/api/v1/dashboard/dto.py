from dataclasses import dataclass


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
    user_request: str = None
