"""
Shared serializer building blocks used across the codebase.
"""

from rest_framework import serializers

from chats.core.audit import AUDIT_FIELDS, is_audit_active


class AuditableModelSerializer(serializers.ModelSerializer):
    """
    ModelSerializer that strips ``created_by`` / ``modified_by`` /
    ``deleted_by`` kwargs out of ``save()`` whenever the audit feature
    flag is OFF for the target project.

    Subclasses MUST override ``_get_audit_project`` when the project
    cannot be derived from ``self.instance.project`` or
    ``self.validated_data["project"]`` (e.g. Queue → sector.project).
    """

    def save(self, **kwargs):
        if not self._is_audit_active():
            for field in AUDIT_FIELDS:
                kwargs.pop(field, None)
        return super().save(**kwargs)

    def _is_audit_active(self) -> bool:
        return is_audit_active(self.context.get("request"), self._get_audit_project())

    def _get_audit_project(self):
        """
        Default resolution: use the instance's project attribute on update,
        or the project value in validated_data on create. Override when
        the audited model does not expose ``project`` directly.
        """
        if self.instance is not None:
            return getattr(self.instance, "project", None)
        validated = getattr(self, "validated_data", None) or {}
        return validated.get("project")
