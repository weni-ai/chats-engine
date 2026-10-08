import logging
import mimetypes
import os
from typing import Optional, Union
from urllib.parse import urlparse

import sentry_sdk
from django.http import StreamingHttpResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response

from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.msgs.models import MessageMedia
from chats.core.requests import get_request_session_with_retries

logger = logging.getLogger(__name__)

DOWNLOAD_CHUNK_SIZE = 8192


def resolve_message_media_for_download(message: ChatMessage) -> Optional[MessageMedia]:
    """Return the first audio media on the message, ordered by created_on."""
    return (
        message.medias.filter(content_type__startswith="audio")
        .order_by("created_on")
        .first()
    )


def get_download_filename(media: MessageMedia) -> str:
    if media.media_file:
        name = os.path.basename(media.media_file.name)
        if name:
            return name
    elif media.media_url:
        name = os.path.basename(urlparse(media.media_url).path)
        if name:
            return name

    ext = mimetypes.guess_extension(media.content_type or "") or ""
    return f"{media.uuid}{ext}"


def build_media_download_response(
    media: MessageMedia, *, log_context: str = "media_download"
) -> Union[Response, StreamingHttpResponse]:
    content_type = media.content_type or "application/octet-stream"
    filename = get_download_filename(media)

    try:
        if media.media_file:
            response = StreamingHttpResponse(
                media.media_file.open("rb").chunks(chunk_size=DOWNLOAD_CHUNK_SIZE),
                content_type=content_type,
            )
        elif media.media_url:
            upstream = get_request_session_with_retries().get(
                media.public_url, stream=True, timeout=30, allow_redirects=True
            )
            upstream.raise_for_status()
            response = StreamingHttpResponse(
                upstream.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE),
                content_type=media.content_type
                or upstream.headers.get("Content-Type", "application/octet-stream"),
            )
        else:
            return Response(
                {"detail": _("Media file not found")},
                status=status.HTTP_404_NOT_FOUND,
            )
    except Exception as error:
        logger.error(
            f"[{log_context}] Failed to fetch media {media.uuid}: {error}"
        )
        sentry_sdk.capture_exception(error)
        return Response(
            {
                "detail": _(
                    "Media couldn't be downloaded due to a technical issue"
                )
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
