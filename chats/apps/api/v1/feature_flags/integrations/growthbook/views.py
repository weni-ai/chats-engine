from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


from chats.apps.api.v1.feature_flags.integrations.growthbook.auth import (
    GrowthbookWebhookSecretAuthentication,
)
from chats.apps.feature_flags.integrations.growthbook.tasks import (
    update_growthbook_feature_flags,
)


class GrowthbookWebhook(GenericViewSet):
    swagger_tag = "Feature Flags"
    authentication_classes = [GrowthbookWebhookSecretAuthentication]
    serializer_class = serializers.Serializer

    def create(self, request, *args, **kwargs):
        update_growthbook_feature_flags.delay()

        return Response(status=status.HTTP_204_NO_CONTENT)
