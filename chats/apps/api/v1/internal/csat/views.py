from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status

from chats.apps.api.authentication.classes import JWTAuthentication
from chats.apps.api.v1.internal.csat.serializers import CSATWebhookSerializer
from chats.apps.api.v1.internal.csat.permissions import CSATWebhookPermission
from chats.apps.csat.models import CSATSurvey


class CSATWebhookView(GenericViewSet):
    serializer_class = CSATWebhookSerializer
    permission_classes = [CSATWebhookPermission]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        CSATSurvey.objects.create(
            room=validated_data["room"],
            rating=validated_data["rating"],
            comment=validated_data.get("comment"),
            answered_on=validated_data["answered_on"],
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
