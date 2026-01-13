from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from sentry_sdk import capture_exception
from django.http import HttpResponseRedirect

from chats.apps.api.v1.archive_chats.serializers import (
    GetArchivedMediaQueryParamsSerializer,
)
from chats.apps.archive_chats.exceptions import InvalidObjectKey
from chats.apps.archive_chats.services import ArchiveChatsService


class GetArchivedMediaView(APIView):
    permission_classes = [AllowAny]

    @property
    def service(self):
        return ArchiveChatsService()

    def get(self, request):
        query_params = GetArchivedMediaQueryParamsSerializer(data=request.query_params)
        query_params.is_valid(raise_exception=True)

        object_key = query_params.validated_data["object_key"]

        try:
            url = self.service.get_archived_media_url(object_key)
        except InvalidObjectKey as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            event_id = capture_exception(e)
            return Response(
                {"error": f"Internal error. Event ID: {event_id}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return HttpResponseRedirect(url)
