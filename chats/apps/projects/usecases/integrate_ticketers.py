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
        projects = Project.objects.filter(org=project.org)

        for project in projects:
            sectors = Sector.objects.filter(project=project)

            # quando chamar via criação de setor unico, pegar apenas o setor que ta sendo criado e nao todos
            for sector in sectors:
                content = {
                    "project_uuid": str(project.uuid),
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
                        detail=f"[{response.status_code}] Error posting the sector/ticketer on flows. Exception: {response.content}"
                    )

    def integrate_topic(self, project):
        # projetos secundarios. Dar exclude no proprio projeto passado pra função.
        projects = Project.objects.filter(org=project.org)

        # percorrendo os projetos que estão na mesma org do projeto principal (os secundarios)
        for secundary_project in projects:
            # queues que fazem parte dos setores do projeto principal
            queues = Queue.objects.filter(sector__project=project)

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
                        detail=f"[{response.status_code}] Error posting the queue on flows. Exception: {response.content}"
                    )


# instance_queue = queue (fila do setor principal)

# content_queue = {
#     "uuid": str(instance_queue.uuid),
#     "name": instance_queue.name,
#     "sector_uuid": str(instance_queue.sector.uuid),
#     "project_uuid": uuid do projeto secundario,
# }
# response = FlowRESTClient().create_queue(**content_queue)


# instance = sector (instancia do setor do projeto principal)
# content = {
#     "project_uuid": uuid do projeto secundario,
#     "name": instance.name,
#     "config": {
#         "project_auth": str(instance.external_token.pk) (do projeto secundário?),
#         "sector_uuid": str(instance.uuid),
#     }
# }
