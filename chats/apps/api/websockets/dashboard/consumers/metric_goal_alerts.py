"""WebSocket consumer that streams metric goal alerts to a project.

The consumer authenticates via the existing ``TokenAuthMiddleware`` and
joins the ``metric_goal_alerts:{project_uuid}`` Channels group. Once
joined, it receives broadcasts produced by the Celery sweep at
``chats.apps.dashboard.tasks.check_metric_goal_violations``.
"""

from __future__ import annotations

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist

from chats.apps.projects.models.models import ProjectPermission

logger = logging.getLogger(__name__)


class MetricGoalAlertConsumer(AsyncJsonWebsocketConsumer):
    """Minimal read-only consumer for metric goal alerts."""

    GROUP_TEMPLATE = "metric_goal_alerts:{project_uuid}"

    async def connect(self):
        self.project_uuid = None
        self.group_name = None

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

        self.group_name = self.GROUP_TEMPLATE.format(project_uuid=self.project_uuid)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if getattr(self, "group_name", None):
            try:
                await self.channel_layer.group_discard(
                    self.group_name, self.channel_name
                )
            except Exception:
                logger.debug("group_discard failed", exc_info=True)

    async def receive_json(self, content, **kwargs):
        if isinstance(content, dict) and content.get("type") == "ping":
            await self.send_json({"type": "pong"})

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
