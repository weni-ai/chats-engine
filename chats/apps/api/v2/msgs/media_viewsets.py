from pydub.exceptions import CouldntDecodeError
from rest_framework import mixins, parsers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v2.msgs.media_permissions import MessageMediaCreatePermissionV2
from chats.apps.api.v2.msgs.media_serializers import MessageMediaCreateSerializerV2
from chats.apps.msgs.models import MessageMedia


class MessageMediaViewSetV2(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Upload media files for a room before creating a message.

    POST /v2/media/
    """

    swagger_tag = "Messages"
    queryset = MessageMedia.objects.all()
    serializer_class = MessageMediaCreateSerializerV2
    parser_classes = [parsers.MultiPartParser]
    permission_classes = [IsAuthenticated, MessageMediaCreatePermissionV2]
    lookup_field = "uuid"

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except CouldntDecodeError:
            return Response(
                {
                    "detail": "Could not decode audio file, possibility of corrupted file",
                    "status": "error",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
