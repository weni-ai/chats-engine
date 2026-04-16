import logging

from django.utils import translation
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.apps.ai_features.history_summary.enums import HistorySummaryFeedbackTags
from chats.apps.ai_features.improve_user_message.services import (
    ImproveUserMessageService,
)
from chats.apps.ai_features.integrations.factories import AIModelPlatformClientFactory
from chats.apps.api.v1.ai_features.serializers import (
    AITextImprovementRequestSerializer,
)
from chats.apps.feature_flags.exceptions import FeatureFlagInactiveError
from chats.apps.projects.models import Project
from chats.core.mixins import LanguageViewMixin

logger = logging.getLogger(__name__)


class HistorySummaryFeedbackTagsView(LanguageViewMixin, APIView):
    """
    API view to get the possible tags for the history summary feedback.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Get the possible tags for the history summary feedback.
        """
        language = self.get_language()

        translation.activate(language)
        results = {}

        for choice in HistorySummaryFeedbackTags:
            results[choice.value] = _(choice.label)

        return Response({"results": results}, status=status.HTTP_200_OK)


class AITextImprovementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AITextImprovementRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]
        improvement_type = serializer.validated_data["type"]
        project_uuid = serializer.validated_data["project_uuid"]

        try:
            project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            return Response(
                {"detail": _("Project not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        integration_client_class = AIModelPlatformClientFactory.get_client_class(
            "bedrock"
        )
        service = ImproveUserMessageService(integration_client_class)

        try:
            improved_text = service.generate_improved_message(
                user_message_text=text,
                improvement_type=improvement_type,
                project=project,
            )
        except FeatureFlagInactiveError:
            return Response(
                {"detail": _("Feature not available for this project.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as exc:
            logger.exception("Error generating improved message")
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"text": improved_text}, status=status.HTTP_200_OK)
