from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from weni.feature_flags.services import FeatureFlagsService

from chats.apps.api.v1.feature_flags.serializers import (
    FeatureFlagsQueryParamsSerializer,
)
from chats.apps.api.v1.permissions import ProjectQueryParamPermission


class FeatureFlagsViewSet(GenericViewSet):
    """
    View for getting the active features for a project.
    """

    swagger_tag = "Feature Flags"

    service = FeatureFlagsService()
    permission_classes = [IsAuthenticated, ProjectQueryParamPermission]
    serializer_class = FeatureFlagsQueryParamsSerializer

    def list(self, request, *args, **kwargs) -> Response:
        """
        Get the active features for a project.
        """

        query_params = FeatureFlagsQueryParamsSerializer(data=request.query_params)
        query_params.is_valid(raise_exception=True)

        user = request.user
        project = query_params.validated_data["project"]

        attributes = {
            "userEmail": user.email,
            "projectUUID": str(project.uuid),
        }

        active_features = self.service.get_active_feature_flags_for_attributes(
            attributes
        )

        return Response({"active_features": active_features}, status=status.HTTP_200_OK)
