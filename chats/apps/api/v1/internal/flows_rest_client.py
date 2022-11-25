import logging
import requests
from django.conf import settings
from rest_framework import status
from chats.apps.api.v1.internal.internal_authorization import InternalAuthentication

LOGGER = logging.getLogger(__name__)


class FlowRESTClient(InternalAuthentication):
    def __init__(self, *args, **kwargs):
        self.base_url = settings.FLOWS_API_URL
        super(self.__class__, self).__init__(*args, **kwargs)

    def create_queue(self, uuid: str, name: str, sector_uuid: str):
        response = requests.post(
            url=f"{self.base_url}/api/v2/internals/ticketers/{sector_uuid}/queues/",
            headers=self.headers,
            json={"uuid": uuid, "name": name},
        )
        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            LOGGER.debug(
                f"[{response.status_code}] Failed to create the queue.  response: {response.content}"
            )
        return response

    def update_queue(self, uuid: str, name: str, sector_uuid: str):
        response = requests.patch(
            url=f"{self.base_url}/api/v2/internals/ticketers/{sector_uuid}/queues/{uuid}/",
            headers=self.headers,
            json={"name": name},
        )
        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            LOGGER.debug(
                f"[{response.status_code}] Failed to update the queue. response: {response.content}"
            )
        return response

    def destroy_queue(self, uuid: str, sector_uuid: str):
        response = requests.delete(
            url=f"{self.base_url}/api/v2/internals/ticketers/{sector_uuid}/queues/{uuid}/",
            headers=self.headers,
        )
        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            LOGGER.debug(
                f"[{response.status_code}] Failed to delete the queue. response: {response.content}"
            )
        return response
