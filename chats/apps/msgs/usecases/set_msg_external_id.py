import logging

import sentry_sdk
from django.db import transaction

from chats.apps.api.utils import create_reply_index
from chats.apps.msgs.models import Message, MessageMedia

logger = logging.getLogger(__name__)


class SetMsgExternalIdUseCase:
    def execute(self, msg_uuid: str, external_id: str):
        try:
            with transaction.atomic():
                try:
                    message = Message.objects.select_for_update().get(uuid=msg_uuid)
                    message.external_id = external_id
                    message.save(update_fields=["external_id"])
                    create_reply_index(message)
                    return
                except Message.DoesNotExist:
                    try:
                        message_media = MessageMedia.objects.select_for_update().get(
                            uuid=msg_uuid
                        )
                        message = message_media.message
                        message.external_id = external_id
                        message.save(update_fields=["external_id"])
                        create_reply_index(message)
                    except MessageMedia.DoesNotExist:
                        # Expected miss: the event may reference a message
                        # that was already archived or never reached the DB.
                        # We log at INFO so it's indexed in Loki but do not
                        # send to Sentry to avoid noise.
                        logger.info(
                            "SetMsgExternalIdUseCase: no Message or MessageMedia "
                            "found for uuid",
                            extra={"msg_uuid": str(msg_uuid)},
                        )
                        return
        except Exception as error:
            # Bug #1 observability: any unexpected error (DB integrity,
            # connection issues, etc.) used to be silently swallowed by a
            # bare ``except Exception: return``, leaving Sentry blind. We
            # now record the failure explicitly but DO NOT re-raise so the
            # consumer keeps acking the message instead of routing it to
            # the dead-letter exchange.
            logger.exception(
                "SetMsgExternalIdUseCase: unexpected error setting external_id",
                extra={"msg_uuid": str(msg_uuid), "external_id": external_id},
            )
            sentry_sdk.capture_exception(error)
            return
