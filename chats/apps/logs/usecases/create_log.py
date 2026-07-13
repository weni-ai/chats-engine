from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models

from chats.apps.logs.models import Log
from chats.apps.logs.utils import compute_changes

User = get_user_model()


class CreateLogUseCase:
    """
    Create a generic audit log for CREATE, UPDATE or DELETE of any model.

    Action is inferred from which objects are provided:
    - ``unchanged_object is None`` + ``object_with_changes`` → CREATE
    - both present → UPDATE
    - ``object_with_changes is None`` + ``unchanged_object`` → DELETE
    """

    def execute(
        self,
        *,
        unchanged_object: models.Model | None,
        object_with_changes: models.Model | None,
        user: User | None = None,
        extra_info: dict | None = None,
        request_info: dict | None = None,
    ) -> Log:
        action, reference = self._resolve_action(
            unchanged_object, object_with_changes
        )
        content_type = ContentType.objects.get_for_model(
            reference, for_concrete_model=False
        )
        changes = compute_changes(unchanged_object, object_with_changes)

        return Log.objects.create(
            action=action,
            content_type=content_type,
            object_id=reference.pk,
            changes=changes,
            user=user,
            extra_info=extra_info or {},
            request_info=request_info or {},
        )

    @staticmethod
    def _resolve_action(
        unchanged_object: models.Model | None,
        object_with_changes: models.Model | None,
    ) -> tuple[str, models.Model]:
        if unchanged_object is None and object_with_changes is not None:
            return Log.Action.CREATE, object_with_changes
        if unchanged_object is not None and object_with_changes is not None:
            return Log.Action.UPDATE, object_with_changes
        if unchanged_object is not None and object_with_changes is None:
            return Log.Action.DELETE, unchanged_object
        raise ValueError(
            "At least one of unchanged_object or object_with_changes must be provided"
        )
