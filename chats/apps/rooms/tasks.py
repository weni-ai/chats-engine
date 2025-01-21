from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.celery import app


@app.task
def update_ticket_on_flows(ticket_uuid: str, user_email: str):
    FlowRESTClient().update_ticket_assignee(ticket_uuid, user_email)
