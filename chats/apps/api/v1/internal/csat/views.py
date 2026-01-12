from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status

from chats.apps.api.authentication.classes import JWTAuthentication
from chats.apps.api.v1.internal.csat.permissions import CSATWebhookPermission
from chats.apps.api.v1.internal.csat.serializers import (
    CreateCSATWebhookSerializer,
    UpdateCSATWebhookSerializer,
)
from chats.apps.csat.models import CSATSurvey


class CSATWebhookView(GenericViewSet):
    serializer_class = CreateCSATWebhookSerializer
    permission_classes = [CSATWebhookPermission]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        room_uuid = request.data.get("room")
        existing_csat_survey = CSATSurvey.objects.filter(room_id=room_uuid).first()

        if existing_csat_survey:
            serializer = UpdateCSATWebhookSerializer(
                existing_csat_survey, data=request.data
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        else:
            serializer = CreateCSATWebhookSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
