from django.conf import settings
from django.db import models, transaction

from chats.apps.event_driven.base_app import EventDrivenAPP

_ACTIONS = {
    (False, True): "CREATE",
    (True, True): "UPDATE",
    (True, False): "DELETE",
}


class ChangeHistoryMixin:
    """Publishes events to the ``change-history.topic`` exchange."""

    def publish_change(self, content: dict) -> None:
        if not getattr(settings, "USE_EDA", False):
            return

        EventDrivenAPP().backend.basic_publish(
            content=content,
            exchange=getattr(
                settings, "CHANGE_HISTORY_EXCHANGE", "change-history.topic"
            ),
            headers={"callback_exchange": settings.DEFAULT_DEAD_LETTER_EXCHANGE},
        )


class PublishChangeHistoryUseCase:
    """
    Publishes a CREATE / UPDATE / DELETE event for any model.

    Does not persist anything locally — only sends to RabbitMQ.
    Body schema is still TBD; payload stays minimal for now.
    """

    def __init__(self, publisher: ChangeHistoryMixin | None = None):
        self._publisher = publisher or ChangeHistoryMixin()

    def execute(
        self,
        *,
        before: models.Model | None = None,
        after: models.Model | None = None,
        user=None,
    ) -> dict:
        action = _ACTIONS.get((before is not None, after is not None))
        if not action:
            raise ValueError("Provide before and/or after")

        reference = after or before
        content = {
            "action": action,
            "model": reference._meta.label_lower,
            "object_id": str(reference.pk),
            "user": getattr(user, "email", None),
        }

        transaction.on_commit(lambda: self._publisher.publish_change(content))
        return content


def publish_change_history(*, before=None, after=None, user=None) -> dict:
    return PublishChangeHistoryUseCase().execute(
        before=before, after=after, user=user
    )
