from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status


class CSATWebhookView(GenericViewSet):
    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_200_OK)
