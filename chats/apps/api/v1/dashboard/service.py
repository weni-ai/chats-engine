from typing import List

from .repository import AgentRepository

from .dto import Agent, Filters


class AgentsService:
    def get_agents_data(self, filters: Filters, project) -> List[Agent]:
        agents_repository = AgentRepository()
        return agents_repository.get_agents_data(filters, project)
