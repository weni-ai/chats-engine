from uuid import UUID

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from chats.apps.assisted_sales.clients import CopilotConnectClient
from chats.apps.assisted_sales.exceptions import (
    CopilotConnectError,
    CopilotIntegrationAlreadyExists,
)
from chats.apps.assisted_sales.models import CopilotIntegration
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector


def build_webchat_connection(connect_data: dict) -> dict:
    channel_uuid = (
        connect_data.get("channel_uuid") or connect_data.get("channelUuid") or ""
    )
    return {
        "socketUrl": settings.WENI_WEBCHAT_SOCKET_URL,
        "channelUuid": str(channel_uuid),
        "host": settings.WENI_WEBCHAT_HOST,
        "connectOn": "mount",
        "storage": "local",
        "callbackUrl": "",
    }


def parse_copilot_uuid(connect_data: dict) -> UUID:
    raw = connect_data.get("uuid") or connect_data.get("project_uuid")
    if not raw:
        raise CopilotConnectError(
            status_code=502,
            error="Connect did not return a copilot project uuid",
        )
    return UUID(str(raw))


def parse_created_on(connect_data: dict):
    value = connect_data.get("created_on")
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value
    return parse_datetime(str(value))


class CreateCopilotIntegrationUseCase:
    def __init__(self, client: CopilotConnectClient = None):
        self.client = client or CopilotConnectClient()

    def execute(
        self,
        *,
        name: str,
        project: Project,
        user,
        sector: Sector = None,
    ) -> CopilotIntegration:
        existing = CopilotIntegration.objects.filter(project=project)
        if sector:
            existing = existing.filter(sector=sector)
        else:
            existing = existing.filter(sector__isnull=True)
        if existing.exists():
            raise CopilotIntegrationAlreadyExists()

        connect_data = self.client.create_copilot_project(
            name=name, project_uuid=str(project.uuid)
        )

        copilot_uuid = parse_copilot_uuid(connect_data)
        assigned_agents = self.client.get_assigned_agents(str(copilot_uuid))
        connection = build_webchat_connection(connect_data)

        return CopilotIntegration.objects.create(
            project=project,
            sector=sector,
            copilot_project_uuid=copilot_uuid,
            name=connect_data.get("name") or name,
            assigned_agents=assigned_agents,
            connection=connection,
            connected_by=user,
            copilot_created_on=parse_created_on(connect_data),
        )


class UpdateCopilotIntegrationUseCase:
    def __init__(self, client: CopilotConnectClient = None):
        self.client = client or CopilotConnectClient()

    def execute(
        self, *, integration: CopilotIntegration, new_uuid: UUID, user
    ) -> CopilotIntegration:
        if str(integration.copilot_project_uuid) == str(new_uuid):
            raise CopilotConnectError(
                status_code=400,
                error="New copilot uuid is the same as the current one",
            )

        connect_data = self.client.switch_copilot_project(
            old_copilot_uuid=str(integration.copilot_project_uuid),
            new_copilot_uuid=str(new_uuid),
        ) or {}

        copilot_uuid = new_uuid
        if connect_data.get("uuid") or connect_data.get("project_uuid"):
            copilot_uuid = parse_copilot_uuid(connect_data)

        assigned_agents = self.client.get_assigned_agents(str(copilot_uuid))

        integration.copilot_project_uuid = copilot_uuid
        integration.name = connect_data.get("name") or integration.name
        integration.assigned_agents = assigned_agents
        integration.connection = build_webchat_connection(connect_data)
        integration.connected_by = user
        integration.connected_on = timezone.now()
        created_on = parse_created_on(connect_data)
        if created_on:
            integration.copilot_created_on = created_on
        integration.save()
        return integration


class RemoveCopilotIntegrationUseCase:
    def __init__(self, client: CopilotConnectClient = None):
        self.client = client or CopilotConnectClient()

    def execute(self, *, integration: CopilotIntegration) -> None:
        self.client.remove_copilot_project(str(integration.copilot_project_uuid))
        integration.delete()


class GetLinkedCopilotUseCase:
    def __init__(self, client: CopilotConnectClient = None):
        self.client = client or CopilotConnectClient()

    def execute(self, *, project: Project, sector: Sector = None) -> CopilotIntegration:
        queryset = CopilotIntegration.objects.filter(project=project)
        if sector:
            queryset = queryset.filter(sector=sector)
        else:
            queryset = queryset.filter(sector__isnull=True)
            if not queryset.exists():
                queryset = CopilotIntegration.objects.filter(project=project)

        integration = queryset.select_related("connected_by").first()
        if not integration:
            raise CopilotIntegration.DoesNotExist()

        assigned_agents = self.client.get_assigned_agents(
            str(integration.copilot_project_uuid)
        )
        if assigned_agents != integration.assigned_agents:
            integration.assigned_agents = assigned_agents
            integration.save(update_fields=["assigned_agents", "modified_on"])
        return integration


class ListExistingCopilotsUseCase:
    def __init__(self, client: CopilotConnectClient = None):
        self.client = client or CopilotConnectClient()

    def execute(self, *, org_uuid: str, name: str = None) -> list:
        connect_projects = self.client.list_copilot_projects(org_uuid, name=name)
        if connect_projects is not None:
            return [
                self._from_connect(item)
                for item in connect_projects
                if item.get("uuid") or item.get("project_uuid")
            ]

        queryset = CopilotIntegration.objects.filter(project__org=str(org_uuid))
        if name:
            queryset = queryset.filter(name__icontains=name)
        queryset = queryset.order_by("name")
        return [self._from_integration(item) for item in queryset]

    def _from_connect(self, item: dict) -> dict:
        copilot_uuid = item.get("uuid") or item.get("project_uuid")
        return {
            "name": item.get("name") or "",
            "assigned_agents": int(
                item.get("assigned_agents", item.get("count", 0)) or 0
            ),
            "uuid": copilot_uuid,
            "project_uuid": item.get("project_uuid") or copilot_uuid,
        }

    def _from_integration(self, integration: CopilotIntegration) -> dict:
        copilot_uuid = str(integration.copilot_project_uuid)
        return {
            "name": integration.name,
            "assigned_agents": integration.assigned_agents,
            "uuid": copilot_uuid,
            "project_uuid": copilot_uuid,
        }
