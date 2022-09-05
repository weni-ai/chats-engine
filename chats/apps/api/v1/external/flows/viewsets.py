from rest_framework import viewsets, status
from rest_framework.response import Response

from chats.apps.projects.models import Flow
from chats.apps.api.v1.external.flows.serializers import FlowSerializer
from chats.apps.api.v1.external.permissions import IsExternalPermission
from chats.apps.projects.models import Project


class FlowViewSet(viewsets.ModelViewSet):
    model = Flow
    queryset = Flow.objects.all()
    serializer_class = FlowSerializer
    permission_classes = [
        IsExternalPermission,
    ]
    lookup_field = "uuid"
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        auth_token = auth_header.split()[1]
        project = Project.objects.get(permissions__uuid=auth_token)
        flow_uuid = request.data.get("project_flows_uuid")
        flow = Flow.objects.create(project_flows_uuid=flow_uuid, project=project)
        serializer = FlowSerializer(flow)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
