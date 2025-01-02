from chats.celery import app


@app.task
def update_ticket_on_flows(ticket_uuid: str, user_email: str):
    pass
