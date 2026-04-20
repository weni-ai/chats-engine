"""
Helpers for populating audit fields (created_by, modified_by, deleted_by)
while respecting the AUDIT_LOG_FEATURE_FLAG_KEY feature flag.

Use ``is_audit_active(request, project)`` to know whether audit data should
be recorded for a given request/project pair, and ``apply_audit_fields``
to conditionally set the audit attributes on an instance before a direct
``.save()`` or ``.delete()`` (paths that bypass a serializer).
"""

from django.conf import settings
from weni.feature_flags.shortcuts import is_feature_active


AUDIT_FIELDS = ("created_by", "modified_by", "deleted_by")


def is_audit_active(request, project) -> bool:
    """
    Return True when the audit feature flag is enabled for the given
    request user + project. Returns False when the project cannot be
    determined or there is no authenticated user in the request.

    Fails open (returns True) when the flag service itself raises, so a
    transient outage does not silently drop audit data the caller asked
    to persist.
    """
    if project is None or request is None:
        return False
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    try:
        return is_feature_active(
            settings.AUDIT_LOG_FEATURE_FLAG_KEY,
            user.email,
            str(project.uuid),
        )
    except Exception:
        return True


def apply_audit_fields(instance, request, project, *, on_delete=False):
    """
    Set modified_by (and deleted_by when ``on_delete=True``) on ``instance``
    only when the audit flag is active for the caller's project.

    Use this for viewset paths that mutate an instance directly and call
    ``.save()`` / ``.delete()`` without going through a serializer
    (e.g. ``perform_destroy`` or custom ``@action`` methods).
    """
    if not is_audit_active(request, project):
        return
    instance.modified_by = request.user
    if on_delete:
        instance.deleted_by = request.user
