from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status

from chats.apps.api.v1.internal.csat.serializers import CSATWebhookSerializer


class CSATWebhookView(GenericViewSet):
    serializer_class = CSATWebhookSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # TODO: Add permission logic
        # TODO: Add saving logic

        return Response(status=status.HTTP_200_OK)
