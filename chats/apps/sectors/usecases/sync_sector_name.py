import logging

from rest_framework import status

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.rooms.exceptions import FlowsTicketerNotFoundError

logger = logging.getLogger(__name__)


class SyncSectorNameToFlows:
    def __init__(self, flows_client=None):
        self.flows_client = flows_client or FlowRESTClient()

    def execute(self, instance):
        try:
            ticketer_uuid = self.flows_client.get_ticketer_by_sector(
                instance.project, str(instance.uuid)
            )
        except FlowsTicketerNotFoundError as exc:
            logger.error(
                "Could not find ticketer to rename sector %s: %s",
                instance.uuid,
                exc,
            )
            return

        response = self.flows_client.update_ticketer(ticketer_uuid, instance.name)
        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            logger.error(
                "[%s] Error updating the sector name on Flows. Exception: %s",
                response.status_code,
                response.content,
            )
