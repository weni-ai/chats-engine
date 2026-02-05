from chats.apps.csat.flows.definitions.flow import (
    CSAT_FLOW_DEFINITION_DATA,
    CSAT_FLOW_VERSION,
)
from django.conf import settings
from datetime import datetime, timedelta
from chats.apps.csat.models import CSATFlowProjectConfig
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


@app.task
def update_all_projects_csat_flow_definition():
    configs = CSATFlowProjectConfig.objects.filter(version__lt=CSAT_FLOW_VERSION)

    expiration_time = datetime.now() + timedelta(
        minutes=settings.CSAT_FLOW_UPDATE_EXPIRATION_TIME
    )

    for config in configs:
        update_project_csat_flow_definition.apply_async(
            args=[config.project.uuid, CSAT_FLOW_DEFINITION_DATA, CSAT_FLOW_VERSION],
            expires=expiration_time,
        )


@app.task
def update_project_csat_flow_definition(
    project_uuid: str, definition: dict, version: int
):
    if definition != CSAT_FLOW_DEFINITION_DATA:
        raise ValueError("Definition is not the current CSAT flow definition")

    if version != CSAT_FLOW_VERSION:
        raise ValueError("Version is not the current CSAT flow version")

    project = Project.objects.get(uuid=project_uuid)

    CSATFlowService(
        flows_client=FlowRESTClient(),
        cache_client=CacheClient(),
        token_generator=JWTTokenGenerator(),
    ).update_csat_flow_definition(project, definition, version)
