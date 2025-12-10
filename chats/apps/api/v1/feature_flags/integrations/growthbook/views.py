from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from chats.apps.api.v1.feature_flags.integrations.growthbook.auth import (
    GrowthbookWebhookSecretAuthentication,
)


class GrowthbookWebhook(GenericViewSet):
    """
    Webhook for Growthbook feature flags updates.
    Note: Feature flag updates are now handled internally by weni-commons library.
    """

    swagger_tag = "Feature Flags"
    authentication_classes = [GrowthbookWebhookSecretAuthentication]
    serializer_class = serializers.Serializer

    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)
