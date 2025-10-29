from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.repository import AgentRepository


class AgentsService:
    def get_agents_data(self, filters: Filters, project):
        agents_repository = AgentRepository()
        return agents_repository.get_agents_data(filters, project)

    def get_agents_custom_status(self, filters: Filters, project):
        agents_repository = AgentRepository()
        return agents_repository.get_agents_custom_status(filters, project)

    def get_agents_csat_score(self, filters: Filters, project):
        agents_repository = AgentRepository()
        return agents_repository.get_agents_csat_score(filters, project)
