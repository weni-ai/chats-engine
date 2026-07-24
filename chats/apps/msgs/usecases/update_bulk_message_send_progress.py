import logging
from typing import Optional
from uuid import UUID

from django.db.models import Count, Q

from chats.apps.msgs.models import (
    BulkMessageSend,
    BulkMessageSendMessage,
    BulkMessageSendMessageStatus,
    BulkMessageSendStatus,
)
from chats.utils.websockets import send_channels_group

logger = logging.getLogger(__name__)


class UpdateBulkMessageSendProgressUseCase:
    """
    Aggregates per-room bulk send outcomes, marks the parent as FINISHED at
    100%, and notifies the requesting user over WebSocket.
    """

    def execute(self, bulk_send_uuid: UUID) -> Optional[dict]:
        bulk_send = BulkMessageSend.objects.filter(uuid=bulk_send_uuid).first()
        if not bulk_send:
            logger.info(
                "[UpdateBulkMessageSendProgressUseCase] BulkMessageSend not found "
                "for UUID: %s",
                bulk_send_uuid,
            )
            return None

        stats = BulkMessageSendMessage.objects.filter(
            bulk_message_send=bulk_send
        ).aggregate(
            success_total=Count(
                "pk", filter=Q(status=BulkMessageSendMessageStatus.SUCCESS)
            ),
            failed_total=Count(
                "pk", filter=Q(status=BulkMessageSendMessageStatus.FAILED)
            ),
        )
        success_total = stats["success_total"] or 0
        failed_total = stats["failed_total"] or 0
        processed = success_total + failed_total
        total_to_send = bulk_send.rooms_qty or 0

        if total_to_send > 0:
            percentage = round((processed / total_to_send) * 100, 2)
        else:
            percentage = 0.0

        if (
            total_to_send > 0
            and processed >= total_to_send
            and bulk_send.status != BulkMessageSendStatus.FINISHED
        ):
            bulk_send.status = BulkMessageSendStatus.FINISHED
            bulk_send.save(update_fields=["status", "modified_on"])
            logger.info(
                "[UpdateBulkMessageSendProgressUseCase] BulkMessageSend %s marked "
                "as FINISHED",
                bulk_send.uuid,
            )

        content = {
            "uuid": str(bulk_send.uuid),
            "percentage": percentage,
            "success_total": success_total,
            "failed_total": failed_total,
            "total_to_send": total_to_send,
        }

        permission = bulk_send.user.project_permissions.filter(
            project=bulk_send.project, is_deleted=False
        ).first()
        if not permission:
            logger.info(
                "[UpdateBulkMessageSendProgressUseCase] No project permission for "
                "user %s on project %s; skipping WS progress update for bulk send %s",
                bulk_send.user_id,
                bulk_send.project_id,
                bulk_send.uuid,
            )
            return content

        send_channels_group(
            group_name=f"permission_{permission.pk}",
            call_type="notify",
            action="bulk_message_progress_update",
            content=content,
        )
        return content
