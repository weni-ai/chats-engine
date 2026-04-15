from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.projects.models import Project

from chats.apps.api.v2.internal.dashboard.serializers import (
    InternalDashboardQueryParamsSerializer,
    DashboardAgentsSerializerV2,
    DashboardCustomStatusByAgentSerializerV2,
)
from chats.apps.api.v2.internal.dashboard.usecases.agents import (
    InternalDashboardAgentsUsecase,
)
from chats.apps.api.v2.internal.dashboard.usecases.custom_status_by_agent import (
    InternalDashboardCustomStatusByAgentUsecase,
)


class InternalDashboardViewsetV2(viewsets.GenericViewSet):
    swagger_tag = "Dashboard"
    lookup_field = "uuid"
    queryset = Project.objects.all()
    serializer_class = DashboardAgentsSerializerV2
    permission_classes = [permissions.IsAuthenticated, ModuleHasPermission]

    @action(
        detail=True,
        methods=["GET"],
        url_name="agent",
    )
    def agent(self, request, *args, **kwargs):
        """Agent metrics for the project or the sector"""
        project = self.get_object()

        serializer = InternalDashboardQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        usecase = InternalDashboardAgentsUsecase()
        agents_data = usecase.execute(project, serializer.validated_data)

        agents = DashboardAgentsSerializerV2(agents_data, many=True)

        return Response({"results": agents.data}, status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["GET"],
        url_name="custom_status_by_agent",
        url_path="custom-status-by-agent",
    )
    def custom_status_by_agent(self, request, *args, **kwargs):
        """Custom status metrics by agent"""
        project = self.get_object()

        serializer = InternalDashboardQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        usecase = InternalDashboardCustomStatusByAgentUsecase()
        agents_data = usecase.execute(project, serializer.validated_data)

        page = self.paginate_queryset(agents_data)
        if page is not None:
            result_serializer = DashboardCustomStatusByAgentSerializerV2(
                page, many=True, context={"project": project}
            )
            return self.get_paginated_response(result_serializer.data)

        result_serializer = DashboardCustomStatusByAgentSerializerV2(
            agents_data, many=True, context={"project": project}
        )

        return Response({"results": result_serializer.data}, status.HTTP_200_OK)
