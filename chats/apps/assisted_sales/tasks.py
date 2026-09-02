from django.conf import settings
from django.db import transaction

from chats.apps.assisted_sales.usecases import SetRoomCopilotChannelUseCase
from chats.celery import app


@app.task(name="assisted_sales.set_room_copilot_channel")
def set_room_copilot_channel(room_pk: str) -> None:
    SetRoomCopilotChannelUseCase().execute(room_pk)


def enqueue_set_room_copilot_channel(room_pk: str) -> None:
    if settings.USE_CELERY:
        transaction.on_commit(
            lambda pk=str(room_pk): set_room_copilot_channel.delay(pk)
        )
        return
    SetRoomCopilotChannelUseCase().execute(room_pk)
