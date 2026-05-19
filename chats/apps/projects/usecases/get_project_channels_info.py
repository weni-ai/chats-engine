from chats.apps.api.v1.internal.rest_clients.connect_rest_client import (
    ConnectRESTClient,
)


class GetProjectChannelsInfoUseCase:
    def __init__(self, project_uuid):
        self.project_uuid = project_uuid
        self.connect_client = ConnectRESTClient()

    def execute(self):
        response = self.connect_client.list_channels(
            project_uuid=self.project_uuid,
            channel_type="WAC",
            exclude_wpp_demo=True,
        )
        return response.json().get("channels", [])
