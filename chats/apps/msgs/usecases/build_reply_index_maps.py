from chats.apps.msgs.models import ChatMessageReplyIndex
from chats.apps.msgs.utils import extract_wamid_core


class BuildReplyIndexMapUseCase:
    """
    Bulk-fetch ChatMessageReplyIndex rows for every replied-to
    external_id in the page, returning a dict keyed by external_id.
    """

    def execute(self, messages) -> dict:
        external_ids = set()
        for msg in messages:
            metadata = msg.metadata if isinstance(msg.metadata, dict) else {}
            context = metadata.get("context")
            if isinstance(context, dict):
                ext_id = context.get("id")
                if ext_id:
                    external_ids.add(ext_id)

        if not external_ids:
            return {}

        return {
            ri.external_id: ri
            for ri in ChatMessageReplyIndex.objects.select_related("message").filter(
                external_id__in=external_ids
            )
        }


class BuildReplyIndexCoreMapUseCase:
    """
    Bulk-fetch ChatMessageReplyIndex rows by stable WAMID core for every
    replied-to id that was *not* resolved by the exact ``external_id``
    lookup. Returns a dict keyed by ``external_id_core`` so callers can
    fall back when Meta sent a different envelope inside ``context.id``.

    Results are scoped to ``room_uuid`` so a core collision can never
    leak a message from another room (or project) into this room's
    history. WhatsApp replies always belong to the same conversation as
    the original message, so this is a safe invariant to enforce.
    """

    def execute(self, messages, exact_map: dict, room_uuid) -> dict:
        unresolved = set()
        for msg in messages:
            metadata = msg.metadata if isinstance(msg.metadata, dict) else {}
            context = metadata.get("context")
            if isinstance(context, dict):
                ext_id = context.get("id")
                if ext_id and ext_id not in exact_map:
                    unresolved.add(ext_id)

        if not unresolved:
            return {}

        cores = {core for core in (extract_wamid_core(eid) for eid in unresolved) if core}
        if not cores:
            return {}

        return {
            ri.external_id_core: ri
            for ri in (
                ChatMessageReplyIndex.objects.select_related("message")
                .filter(external_id_core__in=cores, message__room_id=room_uuid)
                .order_by("created_on")
            )
        }
