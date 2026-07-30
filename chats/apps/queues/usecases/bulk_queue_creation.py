import logging
from typing import List

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, status

from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.internal.eda_clients.change_history_client import (
    publish_change_history,
)
from chats.apps.projects.models import ProjectPermission
from chats.apps.projects.usecases.integrate_ticketers import IntegratedTicketers
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector, SectorGroupSector
from chats.apps.sectors.usecases.group_sector_authorization import (
    QueueGroupSectorAuthorizationCreationUseCase,
)

logger = logging.getLogger(__name__)


class BulkQueueCreationUseCase:
    """
    Orchestrates the bulk creation of queues for a sector.

    Responsibilities:
    - Persist queues and their related queue authorizations.
    - Trigger group sector authorization use case when the sector belongs
      to a group sector.
    - Synchronize each queue with Flows when ``USE_WENI_FLOWS`` is enabled,
      either via ``IntegratedTicketers`` (when the project is principal and
      the sector has a secondary project) or via ``FlowRESTClient``.

    Failure handling:
    - DB-level conflicts (e.g. unique constraint violations) raised during
      persistence are surfaced as 400 ``ValidationError``.
    - Flows synchronization failures abort the surrounding ``transaction.atomic``
      block, which rolls back all DB changes automatically. Queues already
      created on Flows in previous iterations are compensated via
      ``destroy_queue`` calls before re-raising the exception.
    """

    def __init__(
        self,
        sector: Sector,
        queues_data: List[dict],
        user: User,
    ):
        self.sector = sector
        self.queues_data = queues_data
        self.user = user
        self.project = sector.project
        self.has_group_sectors = SectorGroupSector.objects.filter(
            sector=sector
        ).exists()
        self.should_use_integration = bool(
            self.project.config
            and self.project.config.get("its_principal", False)
            and sector.secondary_project
        )

    def _build_queue(self, queue_data: dict) -> Queue:
        queue_limit_data = queue_data.get("queue_limit") or {}
        return Queue.objects.create(
            sector=self.sector,
            name=queue_data["name"],
            queue_purpose=queue_data.get("queue_purpose"),
            config=queue_data.get("config"),
            queue_limit=queue_limit_data.get("limit"),
            # Coerce explicit ``null`` from the serializer (which allows it)
            # to ``False`` because the model column is NOT NULL.
            is_queue_limit_active=bool(queue_limit_data.get("is_active")),
            created_by=self.user,
            modified_by=self.user,
        )

    def _create_queue_authorizations(
        self, queue: Queue, agent_emails: List[str]
    ) -> None:
        if not agent_emails:
            return

        permissions = ProjectPermission.objects.filter(
            project=self.project,
            user__in=[email.lower() for email in agent_emails],
            is_deleted=False,
        )
        authorizations = [
            QueueAuthorization(
                queue=queue,
                permission=perm,
                role=QueueAuthorization.ROLE_AGENT,
                created_by=self.user,
                modified_by=self.user,
            )
            for perm in permissions
        ]
        created = QueueAuthorization.objects.bulk_create(authorizations)
        for auth in created:
            publish_change_history(after=auth, user=self.user)

    def _persist_queues(self) -> List[Queue]:
        created_queues: List[Queue] = []

        for queue_data in self.queues_data:
            agent_emails = queue_data.get("agents", []) or []
            queue = self._build_queue(queue_data)
            publish_change_history(after=queue, user=self.user)
            self._create_queue_authorizations(queue, agent_emails)

            if self.has_group_sectors:
                QueueGroupSectorAuthorizationCreationUseCase(queue).execute()

            created_queues.append(queue)

        return created_queues

    def _sync_queue_with_flows(self, queue: Queue) -> None:
        flows_response = FlowRESTClient().create_queue(
            uuid=str(queue.uuid),
            name=queue.name,
            queue_purpose=queue.queue_purpose,
            sector_uuid=str(self.sector.uuid),
            project_uuid=str(self.project.uuid),
        )
        if flows_response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
        ]:
            raise exceptions.APIException(
                detail=(
                    f"[{flows_response.status_code}] Error posting the queue"
                    f" on flows. Exception: {flows_response.content}"
                )
            )

    def _rollback_flows(self, synced_queues: List[Queue]) -> None:
        for queue in synced_queues:
            try:
                FlowRESTClient().destroy_queue(
                    uuid=str(queue.uuid),
                    sector_uuid=str(self.sector.uuid),
                    project_uuid=str(self.project.uuid),
                )
            except Exception:
                logger.exception(
                    "Failed to rollback queue %s on Flows during bulk create",
                    queue.uuid,
                )

    def execute(self) -> List[Queue]:
        with transaction.atomic():
            try:
                created_queues = self._persist_queues()
            except IntegrityError as exc:
                raise exceptions.ValidationError(
                    {
                        "queues": _(
                            "One or more queue names conflict with existing "
                            "queues in this sector."
                        )
                    }
                ) from exc

            if not settings.USE_WENI_FLOWS:
                return created_queues

            if self.should_use_integration:
                IntegratedTicketers().integrate_individual_topic(
                    self.project, self.sector.secondary_project
                )
                return created_queues

            synced_queues: List[Queue] = []
            try:
                for queue in created_queues:
                    self._sync_queue_with_flows(queue)
                    synced_queues.append(queue)
            except exceptions.APIException:
                self._rollback_flows(synced_queues)
                raise

        return created_queues
