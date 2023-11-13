from rest_framework import parsers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import DiscussionMessage
from ..serializers import (
    DiscussionCreateMessageSerializer,
    DiscussionReadMessageSerializer,
    MessageAndMediaSimpleSerializer,
)
from ..usecases import CreateMessageWithMediaUseCase


class DiscussionMessageActionsMixin:
    """This should be used with a Discussion model viewset"""

    @action(
        detail=True, methods=["POST"], url_name="send_messages", filterset_class=None
    )
    def send_messages(self, request, *args, **kwargs):
        try:
            user = request.user
            discussion = self.get_object()
            serializer = DiscussionCreateMessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            msg = discussion.create_discussion_message(
                message=serializer.validated_data.get("text"), user=user
            )
            serialized_msg = DiscussionReadMessageSerializer(instance=msg)

            return Response(
                serialized_msg.data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as error:
            return Response(
                {"detail": f"{type(error)}: {error}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=True, methods=["GET"], url_name="list_messages", filterset_class=None
    )
    def list_messages(self, request, *args, **kwargs):
        discussion = self.get_object()

        queryset = DiscussionMessage.objects.filter(discussion=discussion)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = DiscussionReadMessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = DiscussionReadMessageSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        methods=["POST"],
        detail=True,
        url_name="create_media",
        parser_classes=[parsers.MultiPartParser],
    )
    def send_media_messages(self, request, *args, **kwargs):
        serializer = MessageAndMediaSimpleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        discussion = self.get_object()
        user = request.user

        message_media = CreateMessageWithMediaUseCase(
            discussion, user, serializer.validated_data
        ).execute()
        serialized_message = DiscussionReadMessageSerializer(
            instance=message_media.message
        )
        headers = self.get_success_headers(serialized_message.data)

        return Response(
            serialized_message.data, status=status.HTTP_201_CREATED, headers=headers
        )
