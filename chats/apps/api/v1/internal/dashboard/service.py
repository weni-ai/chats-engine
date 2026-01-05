from chats.apps.api.v1.internal.dashboard.dto import Filters
from chats.apps.api.v1.internal.dashboard.repository import (
    AgentRepository,
    CSATRepository,
)


class AgentsService:
    def get_agents_data(self, filters: Filters, project):
        agents_repository = AgentRepository()
        return agents_repository.get_agents_data(filters, project)

    def get_agents_custom_status_and_rooms(self, filters: Filters, project):
        agents_repository = AgentRepository()
        return agents_repository.get_agents_custom_status_and_rooms(filters, project)

    def get_agents_custom_status(self, filters: Filters, project):
        agents_repository = AgentRepository()
        return agents_repository.get_agents_custom_status(filters, project)


class CSATService:
    def get_csat_ratings(self, filters: Filters, project):
        csat_repository = CSATRepository()
        return csat_repository.get_csat_ratings(filters, project)
