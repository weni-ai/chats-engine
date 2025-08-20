from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .auth import GrowthbookSignatureAuthentication


class GrowthbookWebhook(GenericViewSet):
    authentication_classes = [GrowthbookSignatureAuthentication]
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_200_OK)
