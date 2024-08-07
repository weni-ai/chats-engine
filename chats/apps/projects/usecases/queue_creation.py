from dataclasses import dataclass

from django.contrib.auth import get_user_model

from chats.apps.queues.models import Queue
from .exceptions import InvalidProjectData

User = get_user_model()


@dataclass
class QueueCreationDTO:
    sector: str
    uuid: str
    name: str
    agents: list
