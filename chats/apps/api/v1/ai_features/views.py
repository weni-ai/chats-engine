from rest_framework.views import APIView


class HistorySummaryFeedbackTagsView(APIView):
    """
    API view to get the possible tags for the history summary feedback.
    """

    def get(self, request, *args, **kwargs):
        """
        Get the possible tags for the history summary feedback.
        """
        language = request.headers.get("Accept-Language")
