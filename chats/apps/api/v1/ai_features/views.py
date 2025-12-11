from django.utils import translation
from django.utils.translation import gettext as _
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


from chats.core.mixins import LanguageViewMixin
from chats.apps.ai_features.history_summary.enums import HistorySummaryFeedbackTags


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
