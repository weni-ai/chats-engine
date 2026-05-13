import logging

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.apps.projects.models import Project
from chats.apps.projects.usecases.exceptions import (
    FlowTemplateChannelsNotFound,
    FlowTemplateNotFound,
)
from chats.apps.projects.usecases.flow_templates import GetFlowTemplatesDataUseCase

logger = logging.getLogger(__name__)


class FlowTemplatesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_uuid):
        flow_uuid = request.query_params.get("flow")

        if not flow_uuid:
            return Response(
                {"detail": "The 'flow' query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        get_object_or_404(Project, uuid=project_uuid)

        usecase = GetFlowTemplatesDataUseCase(project_uuid)

        try:
            result = usecase.execute(flow_uuid)
        except (FlowTemplateNotFound, FlowTemplateChannelsNotFound) as exc:
            logger.warning(
                "Flow templates retrieval failed: project=%s flow=%s error=%s",
                project_uuid,
                flow_uuid,
                exc,
            )
            return Response(
                {"detail": _("Flow template not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        templates = [
            {
                "variables": template.variables,
                "data": template.data,
            }
            for template in result.templates
        ]

        return Response(
            {
                "flow_uuid": str(result.uuid),
                "total_template_qty": len(templates),
                "templates": templates,
            },
            status=status.HTTP_200_OK,
        )
