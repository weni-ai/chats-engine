from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.contacts.serializers import (
    OutOffWhatsappResponseWindowContactSerializer,
)
from chats.apps.contacts.usecases.out_off_whatsapp_response_window import (
    InvalidOutOffWindowFilter,
    build_out_off_window_contact_payload,
    out_off_whatsapp_response_window,
    parse_csv,
)
from chats.apps.projects.models import Project


class OutOffWhatsappResponseWindowContactsView(GenericAPIView):
    """Contacts whose WhatsApp rooms are outside the 24h response window."""

    permission_classes = [IsAuthenticated]
    serializer_class = OutOffWhatsappResponseWindowContactSerializer

    def get(self, request):
        project_uuid = request.query_params.get("project")
        if not project_uuid:
            return Response(
                {"project": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(uuid=project_uuid)
            project.permissions.get(user=request.user)
        except (Project.DoesNotExist, ObjectDoesNotExist, ValidationError, ValueError):
            return Response(
                {"project": "Project not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            contacts, rooms = out_off_whatsapp_response_window(
                project,
                sectors=parse_csv(request.query_params.get("sectors")),
                queues=parse_csv(request.query_params.get("queues")),
                search=request.query_params.get("search"),
            )
        except InvalidOutOffWindowFilter as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        page = self.paginate_queryset(contacts)
        payload = build_out_off_window_contact_payload(page, rooms)
        serializer = self.get_serializer(payload, many=True)
        return self.get_paginated_response(serializer.data)
