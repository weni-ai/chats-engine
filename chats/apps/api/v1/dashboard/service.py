from typing import List

from .dto import Agent, Filters
from .repository import AgentRepository


class AgentsService:
    def get_agents_data(self, filters: Filters, project) -> List[Agent]:
        agents_repository = AgentRepository()
        return agents_repository.get_agents_data(filters, project)
