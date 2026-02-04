from chats.apps.projects.models.models import Project
from chats.celery import app
from chats.apps.rooms.models import Room
from chats.apps.csat.services import CSATFlowService
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.core.cache import CacheClient
from chats.apps.api.authentication.token import JWTTokenGenerator


@app.task
def start_csat_flow(room_uuid: str):
    room = Room.objects.get(uuid=room_uuid)

    CSATFlowService(
        flows_client=FlowRESTClient(),
        cache_client=CacheClient(),
        token_generator=JWTTokenGenerator(),
    ).start_csat_flow(room)


@app.task
def create_csat_flow(project_uuid: str):
    project = Project.objects.get(uuid=project_uuid)

    CSATFlowService(
        flows_client=FlowRESTClient(),
        cache_client=CacheClient(),
        token_generator=JWTTokenGenerator(),
    ).create_csat_flow(project)
