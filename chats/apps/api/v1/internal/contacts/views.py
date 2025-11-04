from rest_framework import status
from rest_framework.views import APIView

from rest_framework.response import Response
from chats.apps.api.v1.internal.contacts.serializers import (
    RoomsContactsInternalQueryParamsSerializer,
    RoomsContactsInternalSerializer,
)
from chats.apps.contacts.models import Contact


class RoomsContactsInternalViewset(APIView):
    serializer_class = RoomsContactsInternalSerializer

    def get(self, request, *args, **kwargs):
        serializer = RoomsContactsInternalQueryParamsSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data["project"]

        contacts = Contact.objects.filter(rooms__queue__sector__project=project)
        return Response(
            RoomsContactsInternalSerializer(contacts, many=True).data,
            status=status.HTTP_200_OK,
        )
