from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..app_services.feedbacks import create_discussion_feedback_message
from ..models import DiscussionUser
from ..serializers import DiscussionUserListSerializer

User = get_user_model()


class DiscussionUserActionsMixin:
    """This should be used with a Discussion model viewset"""

    @action(detail=True, methods=["POST"], url_name="add_agents", filterset_class=None)
    def add_agents(self, request, *args, **kwargs):
        try:
            user = request.data.get("user_email")
            user = User.objects.get(email=user)
            discussion = self.get_object()
            added_agent = discussion.create_discussion_user(
                from_user=request.user, to_user=user
            )
            feedback = {"user": added_agent.user.first_name}
            create_discussion_feedback_message(discussion, feedback, "da")

            return Response(
                {
                    "first_name": added_agent.user.first_name,
                    "last_name": added_agent.user.last_name,
                    "role": added_agent.role,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as error:
            return Response(
                {"detail": f"{type(error)}: {error}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
