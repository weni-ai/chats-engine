"""WebSocket consumer that streams metric goal alerts to a project.

The consumer authenticates via the existing ``TokenAuthMiddleware`` and
joins two Channels groups:

* ``metric_goal_alerts.{project_uuid}`` — project-wide events
  (``metric_goal.violated`` / ``update`` / ``resolved``) for every
  dashboard viewer.
* ``metric_goal_alerts.{project_uuid}.{user_hash}`` — toast events
  (``metric_goal.alert``) fan-out only to configured email recipients.
"""

from __future__ import annotations

import hashlib
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist

from chats.apps.dashboard.services.metric_goal_alerts import (
    is_metric_goal_alerts_enabled,
)
from chats.apps.projects.models.models import ProjectPermission

logger = logging.getLogger(__name__)


class MetricGoalAlertConsumer(AsyncJsonWebsocketConsumer):
    """Minimal read-only consumer for metric goal alerts."""

    # Channels group names only accept ``[A-Za-z0-9._-]`` and are capped
    # at 100 chars. We use ``.`` as separator since ``:`` isn't allowed.
    PROJECT_GROUP_TEMPLATE = "metric_goal_alerts.{project_uuid}"
    USER_GROUP_TEMPLATE = "metric_goal_alerts.{project_uuid}.{user_hash}"

    @classmethod
    def project_group_name(cls, project_uuid: str) -> str:
        return cls.PROJECT_GROUP_TEMPLATE.format(project_uuid=project_uuid)

    @classmethod
    def group_name_for(cls, project_uuid: str, user_email: str) -> str:
        """Per-user group used for toast (``metric_goal.alert``) fan-out."""
        normalized = user_email.strip().lower().encode("utf-8")
        user_hash = hashlib.sha1(normalized).hexdigest()[:16]
        return cls.USER_GROUP_TEMPLATE.format(
            project_uuid=project_uuid,
            user_hash=user_hash,
        )

    async def connect(self):
        self.project_uuid = None
        self.project_group_name = None
        self.user_group_name = None

        try:
            self.user = self.scope["user"]
            self.project_uuid = self.scope["query_params"].get("project", [None])[0]
        except (KeyError, TypeError, AttributeError):
            await self.close()
            return

        if (
            self.user is None
            or getattr(self.user, "is_anonymous", True)
            or not self.project_uuid
            or not getattr(self.user, "email", None)
        ):
            await self.close()
            return

        try:
            permission = await self._get_permission(self.user, self.project_uuid)
        except ObjectDoesNotExist:
            await self.close()
            return

        if not await self._can_view_dashboard(permission):
            await self.close()
            return

        if not await database_sync_to_async(is_metric_goal_alerts_enabled)(
            self.project_uuid
        ):
            await self.close()
            return

        self.project_group_name = MetricGoalAlertConsumer.project_group_name(
            self.project_uuid
        )
        self.user_group_name = MetricGoalAlertConsumer.group_name_for(
            self.project_uuid, self.user.email
        )
        # Backwards-compat alias used by disconnect / older call sites.
        self.group_name = self.user_group_name
        await self.channel_layer.group_add(self.project_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        for name in (self.project_group_name, self.user_group_name):
            if not name:
                continue
            try:
                await self.channel_layer.group_discard(name, self.channel_name)
            except Exception:
                logger.debug("group_discard failed", exc_info=True)

    async def receive_json(self, content, **kwargs):
        if isinstance(content, dict) and content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def metric_goal_alert(self, event):
        await self._forward(event, "metric_goal.alert")

    async def metric_goal_violated(self, event):
        await self._forward(event, "metric_goal.violated")

    async def metric_goal_update(self, event):
        await self._forward(event, "metric_goal.update")

    async def metric_goal_resolved(self, event):
        await self._forward(event, "metric_goal.resolved")

    async def _forward(self, event, default_action: str):
        action = event.get("action", default_action)
        raw_content = event.get("content")
        if isinstance(raw_content, str):
            try:
                content = json.loads(raw_content)
            except (TypeError, ValueError):
                content = raw_content
        else:
            content = raw_content

        await self.send_json({"type": action, "content": content})

    @database_sync_to_async
    def _get_permission(self, user, project_uuid: str) -> ProjectPermission:
        return ProjectPermission.objects.select_related("project").get(
            user=user, project__uuid=project_uuid
        )

    @database_sync_to_async
    def _can_view_dashboard(self, permission: ProjectPermission) -> bool:
        if permission.is_admin:
            return True
        return permission.sector_authorizations.exists()
