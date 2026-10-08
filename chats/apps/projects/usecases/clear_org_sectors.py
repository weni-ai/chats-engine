import logging

from django.conf import settings
from django.db import transaction
from rest_framework import status

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.rooms.services.bulk_close_service import BulkCloseService
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

logger = logging.getLogger(__name__)

SAC_UNIFICADO_END_BY = "sac_unificado"
_FLOWS_OK = {
    status.HTTP_200_OK,
    status.HTTP_201_CREATED,
    status.HTTP_204_NO_CONTENT,
}


class ClearOrgSectorsError(Exception):
    pass


class ClearOrgSectorsUseCase:
    """Delete sectors and queues of an org before a SAC unificado migration."""

    def execute(self, project, user_email=""):
        sectors = list(
            Sector.objects.select_related("project").filter(project__org=project.org)
        )
        if not sectors:
            return

        with transaction.atomic():
            self._close_active_rooms(project)
            for sector in sectors:
                self._delete_sector(sector, user_email)

    def _close_active_rooms(self, project):
        rooms = Room.objects.filter(
            queue__sector__project__org=project.org,
            is_active=True,
        )
        if not rooms.exists():
            return

        logger.info(
            "Closing active rooms before deleting sectors of org %s",
            project.org,
        )
        BulkCloseService().close(rooms=rooms, end_by=SAC_UNIFICADO_END_BY)

    def _delete_sector(self, sector, user_email):
        if settings.USE_WENI_FLOWS:
            self._destroy_on_flows(sector, user_email)
        sector.delete()

    def _destroy_on_flows(self, sector, user_email):
        client = FlowRESTClient()
        project_uuid = self._flows_project_uuid(sector)
        queues = list(sector.queues.filter(is_deleted=False))

        for queue in queues:
            response = client.destroy_queue(
                uuid=str(queue.uuid),
                sector_uuid=str(sector.uuid),
                project_uuid=project_uuid,
            )
            if response.status_code == status.HTTP_404_NOT_FOUND:
                continue
            if response.status_code not in _FLOWS_OK:
                raise ClearOrgSectorsError(
                    f"[{response.status_code}] Error deleting queue {queue.uuid} on flows."
                )

        response = client.destroy_sector(
            sector_uuid=str(sector.uuid),
            user_email=user_email,
        )
        if response.status_code not in _FLOWS_OK:
            raise ClearOrgSectorsError(
                f"[{response.status_code}] Error deleting sector {sector.uuid} on flows."
            )

    def _flows_project_uuid(self, sector):
        secondary = sector.secondary_project or {}
        if isinstance(secondary, dict) and secondary.get("uuid"):
            return str(secondary["uuid"])
        return str(sector.project.uuid)
