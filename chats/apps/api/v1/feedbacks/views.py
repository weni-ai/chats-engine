from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from weni.feature_flags.services import FeatureFlagsService

from chats.apps.api.v1.feedbacks.serializers import FeedbackSerializer
from chats.apps.api.v1.permissions import ProjectBodyPermission
from chats.apps.feedbacks.services import UserFeedbackService
from chats.core.cache import CacheClient


class FeedbackViewSet(GenericViewSet):
    """
    Viewset for feedback creation.
    """

    feedback_service = UserFeedbackService(
        cache_client=CacheClient(),
        feature_flags_service=FeatureFlagsService(),
    )
    serializer_class = FeedbackSerializer

    @property
    def permission_classes(self):
        """
        Permission classes for the viewset.
        """
        permissions = [IsAuthenticated]

        if self.action == "create":
            permissions.append(ProjectBodyPermission)

        return permissions

    def get(self, request, *args, **kwargs) -> Response:
        """
        Get feedback form.
        """
        user = request.user
        should_show_feedback_form = self.feedback_service.should_show_feedback_form(
            user
        )

        return Response(
            {
                "should_show_feedback_form": should_show_feedback_form,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs) -> Response:
        """
        Create feedback.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not self.feedback_service.can_create_feedback(
            user=request.user,
        ):
            raise PermissionDenied

        self.feedback_service.create_feedback(
            user=request.user,
            project=serializer.validated_data["project"],
            rating=serializer.validated_data["rating"],
            comment=serializer.validated_data["comment"],
        )

        return Response(status=status.HTTP_201_CREATED)
