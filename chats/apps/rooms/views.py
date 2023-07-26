from django.conf import settings
from django.db import transaction

from chats.apps.dashboard.tasks import close_metrics, generate_metrics


def close_room(room_pk: str):
    if settings.USE_CELERY:
        transaction.on_commit(
            lambda: close_metrics.apply_async(
                args=[room_pk], queue=settings.METRICS_CUSTOM_QUEUE
            )
        )
    generate_metrics(room_pk)
