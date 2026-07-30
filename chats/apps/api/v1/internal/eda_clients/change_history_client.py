import logging

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from weni_commons.change_history import Action, Entity, Module, Notifier

logger = logging.getLogger(__name__)


def _entity_for(instance: models.Model):
    label = instance._meta.label_lower
    if label == "queues.queue":
        return Entity.QUEUE
    if label == "queues.queueauthorization":
        return Entity.USER
    raise ValueError("Unsupported model for change history: %s" % label)


def _action_for(before, after, reference):
    if before is None:
        if reference._meta.label_lower == "queues.queueauthorization":
            return Action.ADD
        return Action.CREATE
    if after is None:
        return Action.DELETE
    return Action.UPDATE


def _object_name(instance: models.Model) -> str:
    if getattr(instance, "name", None):
        return str(instance.name)
    user = getattr(instance, "user", None)
    if user is not None and getattr(user, "email", None):
        return user.email
    return str(instance.pk)


def _value_diff(before, after):
    if before is None or after is None:
        return None, None
    if hasattr(before, "name") and before.name != after.name:
        return str(before.name), str(after.name)
    if hasattr(before, "role") and before.role != after.role:
        return str(before.role), str(after.role)
    return None, None


def _user_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def publish_change_history(before=None, after=None, user=None, request=None):
    """
    Publish a change-history event via weni-commons ``Notifier``.

    Infers CREATE/ADD/UPDATE/DELETE from ``before`` / ``after``.
    Payload fields are captured immediately so soft-delete mutations that
    happen before ``on_commit`` do not leak into the event.
    """
    if before is None and after is None:
        raise ValueError("Provide before and/or after")

    if not getattr(settings, "AMQ_BROKER_HOST", ""):
        logger.debug("Skipping change history publish: AMQ_BROKER_HOST is not set")
        return

    reference = after or before
    action = _action_for(before, after, reference)
    entity = _entity_for(reference)
    old_value, new_value = _value_diff(before, after)
    project_uuid = str(reference.project.uuid)
    user_email = getattr(user, "email", None) or ""
    object_id = str(reference.pk)
    object_name = _object_name(reference)
    model_label = reference._meta.label_lower
    user_ip = _user_ip(request)

    def _send():
        try:
            Notifier.notify_change(
                project_uuid,
                user_email,
                timezone.now(),
                action,
                entity,
                Module.LIVE_DESK,
                object_id=object_id,
                object_name=object_name,
                old_value=old_value,
                new_value=new_value,
                user_ip=user_ip,
            )
        except Exception:
            logger.exception(
                "Failed to publish change history for %s %s",
                model_label,
                object_id,
            )

    transaction.on_commit(_send)
