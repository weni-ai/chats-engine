from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.discussions.serializers.discussions import (
    AddAgentToDiscussionSerializer,
)

from chats.apps.discussions.models.discussion_user import DiscussionUser
from chats.apps.discussions.serializers.discussion_users import (
    DiscussionUserListSerializer,
)
from chats.apps.discussions.usecases import AddUserToDiscussionUseCase


class DiscussionUserActionsMixin:
    """This should be used with a Discussion model viewset"""

    @action(detail=True, methods=["POST"], url_name="add_agents", filterset_class=None)
    def add_agents(self, request, *args, **kwargs):
        serializer = AddAgentToDiscussionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        discussion = self.get_object()
        result = AddUserToDiscussionUseCase().execute(
            discussion=discussion,
            user_email=serializer.validated_data["user_email"],
            from_user=request.user,
        )

        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["GET"], url_name="list_agents", filterset_class=None)
    def list_agents(self, request, *args, **kwargs):
        discussion = self.get_object()

        queryset = DiscussionUser.objects.filter(discussion=discussion)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = DiscussionUserListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = DiscussionUserListSerializer(queryset, many=True)
        return Response(serializer.data)
