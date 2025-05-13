import logging

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Max, OuterRef, Subquery

from chats.apps.ai_features.models import FeaturePrompt
from chats.apps.api.v1.internal.ai_features.auth.classes import AIFeaturesAuthentication
from chats.apps.api.v1.internal.ai_features.serializers import (
    FeaturePromptReadSerializer,
    FeaturePromptWriteSerializer,
)

logger = logging.getLogger(__name__)


class FeaturePromptsView(APIView):
    """
    API view to create a new feature prompt.
    """

    authentication_classes = [AIFeaturesAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        """
        Create a new feature prompt.
        """

        logger.info(f"Creating new feature prompt: {request.data}")

        serializer = FeaturePromptWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request: Request) -> Response:
        """
        Get all feature prompts, returning only the latest version for each feature.
        """

        # Get the latest version for each feature
        latest_versions = (
            FeaturePrompt.objects.filter(feature=OuterRef("feature"))
            .values("feature")
            .annotate(max_version=Max("version"))
            .values("max_version")
        )

        # Get only the prompts with the latest version
        feature_prompts = FeaturePrompt.objects.filter(
            version=Subquery(latest_versions)
        )
        serializer = FeaturePromptReadSerializer(feature_prompts, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
