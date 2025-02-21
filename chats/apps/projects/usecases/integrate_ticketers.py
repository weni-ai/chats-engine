from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue

from chats.apps.api.v1.internal.rest_clients.connect_rest_client import (
    ConnectRESTClient,
)
from rest_framework import exceptions, status
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient


class IntegratedTicketers:
    def integrate_ticketer(self, project):
        projects = Project.objects.filter(org=project.org, config__its_secundary=True)

        for secundary_project in projects:
            sectors = Sector.objects.filter(
                project=project,
                config__integration_token=str(secundary_project.uuid),
            )

            for sector in sectors:
                content = {
                    "project_uuid": str(secundary_project.uuid),
                    "name": sector.name,
                    "config": {
                        "project_auth": str(sector.external_token.pk),
                        "sector_uuid": str(sector.uuid),
                    },
                }
                connect = ConnectRESTClient()
                response = connect.create_ticketer(**content)

                if response.status_code not in [
                    status.HTTP_200_OK,
                    status.HTTP_201_CREATED,
                ]:
                    raise exceptions.APIException(
                        detail=(
                            f"[{response.status_code}] Error posting the sector/ticketer "
                            f"on flows. Exception: {response.content}"
                        )
                    )

    def integrate_topic(self, project):
        projects = Project.objects.filter(org=project.org, config__its_secundary=True)

        for secundary_project in projects:
            queues = Queue.objects.filter(
                sector__project=project,
                sector__config__integration_token=str(secundary_project.uuid),
            )

            for queue in queues:
                content = {
                    "uuid": str(queue.uuid),
                    "name": queue.name,
                    "sector_uuid": str(queue.sector.uuid),
                    "project_uuid": str(secundary_project.uuid),
                }
                response = FlowRESTClient().create_queue(**content)
                if response.status_code not in [
                    status.HTTP_200_OK,
                    status.HTTP_201_CREATED,
                ]:
                    raise exceptions.APIException(
                        detail=(
                            f"[{response.status_code}] Error posting the queue on flows. "
                            f"Exception: {response.content}"
                        )
                    )

    def integrate_individual_ticketer(self, project, integrated_token):
        try:
            sector = Sector.objects.get(
                project=project, config__integration_token=str(integrated_token)
            )
            content = {
                "project_uuid": str(sector.config.get("integration_token")),
                "name": sector.name,
                "config": {
                    "project_auth": str(sector.external_token.pk),
                    "sector_uuid": str(sector.uuid),
                },
            }
            connect = ConnectRESTClient()
            response = connect.create_ticketer(**content)
            if response.status_code not in [
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ]:
                raise exceptions.APIException(
                    detail=(
                        f"[{response.status_code}] Error posting the sector/ticketer "
                        f"on flows. Exception: {response.content}"
                    )
                )
        except Exception as e:
            raise exceptions.APIException(
                detail=f"There is no secondary project for that sector. Error: {e}"
            )

    def integrate__individual_topic(self, project, sector_integrated_token):
        try:
            queue = Queue.objects.filter(
                sector__project=project,
                sector__config__integration_token=str(sector_integrated_token),
            )
            content = {
                "uuid": str(queue.uuid),
                "name": queue.name,
                "sector_uuid": str(queue.sector.uuid),
                "project_uuid": str(queue.sector.config.get("integration_token")),
            }
            response = FlowRESTClient().create_queue(**content)
            if response.status_code not in [
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ]:
                raise exceptions.APIException(
                    detail=(
                        f"[{response.status_code}] Error posting the queue on flows. "
                        f"Exception: {response.content}"
                    )
                )
        except Exception as e:
            raise exceptions.APIException(
                detail=f"There is no secondary project for that queue. Error: {e}"
            )
