from dataclasses import dataclass

from chats.apps.projects.models import Project, ProjectPermission


EXCLUDED_DOMAINS = ["weni.ai", "vtex.com", "inspiria.studio"]


def should_exclude_admin_domains(user_email: str) -> bool:
    """
    Verifica se o email do usuário pertence a algum dos domínios administrativos.
    Retorna True se o usuário tem privilégios de admin (não deve ser excluído).
    """
    if not user_email:
        return False

    return any(domain in user_email for domain in EXCLUDED_DOMAINS)


def get_admin_domains_exclude_filter():
    """
    Retorna um filtro Q para excluir usuários com domínios administrativos.
    """
    from django.db.models import Q

    exclude_filter = Q()
    for domain in EXCLUDED_DOMAINS:
        exclude_filter |= Q(email__endswith=domain)

    return exclude_filter


@dataclass
class Agent:
    first_name: str = None
    last_name: str = None
    email: str = None
    agent_status: str = None
    closed_rooms: int = None
    opened_rooms: int = None


@dataclass
class Sector:
    uuid: str = None
    name: str = None
    waiting_time: int = None
    response_time: int = None
    interact_time: int = None


@dataclass
class Filters:
    start_date: str = None
    end_date: str = None
    agent: str = None
    sector: list | str = None
    queue: list | str = None
    tag: list | str = None
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
