from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import models
from django.db.models.fields.files import FieldFile
from django.http import HttpRequest

IGNORED_FIELDS = frozenset(
    {
        "uuid",
        "created_on",
        "modified_on",
        "created_by",
        "modified_by",
        "deleted_by",
        "created_by_id",
        "modified_by_id",
        "deleted_by_id",
    }
)


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, FieldFile):
        return value.name or None
    if isinstance(value, models.Model):
        return str(value.pk)
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _iter_concrete_field_names(instance: models.Model) -> list[str]:
    return [
        field.name
        for field in instance._meta.concrete_fields
        if field.name not in IGNORED_FIELDS
        and not isinstance(field, models.ManyToManyField)
    ]


def _get_field_value(instance: models.Model, field_name: str) -> Any:
    field = instance._meta.get_field(field_name)
    if isinstance(field, models.ForeignKey):
        return getattr(instance, field.attname)
    return getattr(instance, field_name)


def snapshot_instance(instance: models.Model) -> dict:
    """Return a serializable snapshot of the instance's relevant fields."""
    return {
        field_name: _serialize_value(_get_field_value(instance, field_name))
        for field_name in _iter_concrete_field_names(instance)
    }


def compute_changes(
    unchanged_object: models.Model | None,
    object_with_changes: models.Model | None,
) -> dict:
    """
    Build the ``changes`` payload for a log entry.

    - CREATE / DELETE: flat snapshot ``{field: value}``
    - UPDATE: only changed fields as ``{field: {"from": old, "to": new}}``
    """
    if unchanged_object is None and object_with_changes is not None:
        return snapshot_instance(object_with_changes)

    if object_with_changes is None and unchanged_object is not None:
        return snapshot_instance(unchanged_object)

    if unchanged_object is None or object_with_changes is None:
        raise ValueError(
            "Both unchanged_object and object_with_changes are required for UPDATE"
        )

    changes: dict = {}
    for field_name in _iter_concrete_field_names(object_with_changes):
        old_value = _serialize_value(_get_field_value(unchanged_object, field_name))
        new_value = _serialize_value(_get_field_value(object_with_changes, field_name))
        if old_value != new_value:
            changes[field_name] = {"from": old_value, "to": new_value}
    return changes


def get_info_from_request(request: HttpRequest) -> dict:
    """Extract IP and User-Agent from an HTTP request for ``request_info``."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")

    return {
        "ip": ip,
        "user_agent": request.META.get("HTTP_USER_AGENT"),
    }
