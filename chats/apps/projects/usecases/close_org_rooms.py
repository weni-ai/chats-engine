import logging

from chats.apps.api.v1.rooms.services.bulk_close_service import BulkCloseService
from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)

SAC_UNIFICADO_END_BY = "sac_unificado"


class CloseOrgRoomsUseCase:
    """Close every active room of the org when a project becomes principal."""

    def execute(self, project, closed_by=None):
        rooms = Room.objects.filter(
            queue__sector__project__org=project.org,
            is_active=True,
        )
        if not rooms.exists():
            return None

        logger.info(
            "Closing active rooms for org %s during SAC unificado migration",
            project.org,
        )
        return BulkCloseService().close(
            rooms=rooms,
            end_by=SAC_UNIFICADO_END_BY,
            closed_by=closed_by,
        )
