from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework import status

from chats.apps.api.v1.dashboard.metric_goals.constants import VALID_METRICS
from chats.apps.api.v1.dashboard.metric_goals.serializers import (
    MetricGoalReadSerializer,
    MetricGoalWriteSerializer,
    _can_configure_metric_goals,
)
from chats.apps.dashboard.models import MetricGoal
from chats.apps.dashboard.services.metric_goal_alerts import (
    is_metric_goal_alerts_enabled,
)
from chats.apps.projects.models import ProjectPermission


class MetricGoalActionsMixin:
    def _get_project_permission(self, project):
        try:
            return project.permissions.get(user=self.request.user)
        except ProjectPermission.DoesNotExist:
            raise PermissionDenied("Você não tem permissão neste projeto")

    def _ensure_feature_enabled(self, project):
        if not is_metric_goal_alerts_enabled(str(project.uuid)):
            raise PermissionDenied(
                "A feature de alertas de meta não está disponível para este projeto"
            )

    def _ensure_can_configure(self, project):
        self._ensure_feature_enabled(project)
        permission = self._get_project_permission(project)
        if not _can_configure_metric_goals(permission):
            raise PermissionDenied("Apenas moderadores podem configurar metas")
        return permission

    def _ensure_can_view(self, project):
        self._ensure_feature_enabled(project)
        permission = self._get_project_permission(project)
        if not (permission.is_admin or permission.sector_authorizations.exists()):
            raise PermissionDenied("Você não tem acesso ao dashboard deste projeto")
        return permission

    def _validate_metric(self, metric):
        if metric not in VALID_METRICS:
            raise ValidationError({"metric": [f"Métrica inválida: {metric}"]})

    @action(
        detail=True,
        methods=["GET"],
        url_path="metric-goals",
        url_name="metric-goals-list",
    )
    def metric_goals_list(self, request, uuid=None):
        """Lista as metas de tempo configuradas para o projeto."""
        project = self.get_object()
        self._ensure_can_view(project)

        goals = (
            MetricGoal.objects.filter(project=project)
            .prefetch_related("recipients__user")
            .order_by("metric")
        )
        serializer = MetricGoalReadSerializer(goals, many=True)
        return Response({"goals": serializer.data}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["POST", "DELETE"],
        url_path=r"metric-goals/(?P<metric>[\w_]+)",
        url_name="metric-goals-detail",
    )
    def metric_goals_detail(self, request, uuid=None, metric=None):
        """Cria, atualiza ou remove a meta de tempo de uma métrica."""
        project = self.get_object()
        self._validate_metric(metric)

        if request.method == "DELETE":
            return self._delete_metric_goal(project, metric)

        return self._upsert_metric_goal(project, metric, request.data)

    def _upsert_metric_goal(self, project, metric, data):
        self._ensure_can_configure(project)

        serializer = MetricGoalWriteSerializer(
            data=data,
            context={"project": project},
        )
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        recipient_permissions = serializer.context.get("recipient_permissions", [])

        goal, _created = MetricGoal.objects.update_or_create(
            project=project,
            metric=metric,
            defaults={
                "threshold_seconds": validated_data["threshold_seconds"],
                "unit": validated_data.get("unit", MetricGoal.UNIT_SECOND),
                "is_active": validated_data.get("is_active", True),
                "email_enabled": validated_data.get("email_enabled", False),
                "rooms_threshold_count": validated_data.get(
                    "rooms_threshold_count",
                    MetricGoal.DEFAULT_ROOMS_THRESHOLD_COUNT,
                ),
                "rooms_threshold_percent": validated_data.get(
                    "rooms_threshold_percent"
                ),
            },
        )

        if "recipients" in validated_data:
            goal.recipients.set(recipient_permissions)

        goal = (
            MetricGoal.objects.filter(pk=goal.pk)
            .prefetch_related("recipients__user")
            .first()
        )
        response_serializer = MetricGoalReadSerializer(goal)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def _delete_metric_goal(self, project, metric):
        self._ensure_can_configure(project)

        try:
            goal = MetricGoal.objects.get(project=project, metric=metric)
        except MetricGoal.DoesNotExist:
            raise NotFound("Meta não configurada para esta métrica")

        goal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
