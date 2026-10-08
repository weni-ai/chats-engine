from rest_framework import serializers

from chats.apps.api.v1.dashboard.metric_goals.constants import (
    UNIT_TO_SECONDS,
    threshold_seconds_to_unit_value,
)
from chats.apps.dashboard.models import MetricGoal
from chats.apps.projects.models import ProjectPermission
from chats.apps.sectors.models import SectorAuthorization


class MetricGoalRecipientReadSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ProjectPermission
        fields = ["first_name", "last_name", "email"]


class MetricGoalReadSerializer(serializers.ModelSerializer):
    recipients = MetricGoalRecipientReadSerializer(many=True, read_only=True)
    threshold_value = serializers.SerializerMethodField()

    class Meta:
        model = MetricGoal
        fields = [
            "metric",
            "threshold_seconds",
            "threshold_value",
            "unit",
            "is_active",
            "email_enabled",
            "rooms_threshold_count",
            "rooms_threshold_percent",
            "recipients",
        ]

    def get_threshold_value(self, goal: MetricGoal) -> int:
        return threshold_seconds_to_unit_value(goal.threshold_seconds, goal.unit)


class MetricGoalRecipientWriteSerializer(serializers.Serializer):
    email = serializers.EmailField()


class MetricGoalWriteSerializer(serializers.Serializer):
    threshold = serializers.IntegerField(min_value=1, required=False)
    threshold_seconds = serializers.IntegerField(min_value=1, required=False)
    unit = serializers.ChoiceField(
        choices=[choice[0] for choice in MetricGoal.UNIT_CHOICES],
        default=MetricGoal.UNIT_SECOND,
    )
    is_active = serializers.BooleanField(default=True)
    email_enabled = serializers.BooleanField(default=False)
    rooms_threshold_count = serializers.IntegerField(
        min_value=0,
        default=MetricGoal.DEFAULT_ROOMS_THRESHOLD_COUNT,
    )
    rooms_threshold_percent = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=False,
        allow_null=True,
    )
    recipients = MetricGoalRecipientWriteSerializer(many=True, required=False)

    def validate(self, attrs):
        threshold = attrs.get("threshold")
        threshold_seconds = attrs.get("threshold_seconds")

        if threshold is None and threshold_seconds is None:
            raise serializers.ValidationError(
                "Informe threshold ou threshold_seconds"
            )

        unit = attrs.get("unit", MetricGoal.UNIT_SECOND)
        if threshold is not None:
            attrs["threshold_seconds"] = threshold * UNIT_TO_SECONDS[unit]
        else:
            attrs["threshold_seconds"] = threshold_seconds

        # `rooms_threshold_count` only gates the email notification (the
        # WS/toast/widget alert fires with a single room in breach). The
        # front sends `0` when email is disabled, since the field is
        # meaningless in that case — we accept and store it as-is instead
        # of silently rewriting the user's input. Whenever `email_enabled`
        # is (re)enabled through this same serializer, a real (>=1) value
        # is required below, so a stale `0` can never end up backing an
        # active email notification.
        email_enabled = attrs.get("email_enabled", False)
        rooms_threshold_count = attrs.get("rooms_threshold_count")
        if email_enabled and rooms_threshold_count == 0:
            raise serializers.ValidationError(
                {
                    "rooms_threshold_count": [
                        "Informe a quantidade de salas para o envio de e-mail"
                    ]
                }
            )

        return attrs

    def validate_recipients(self, recipients):
        project = self.context["project"]
        emails = [item["email"] for item in recipients]
        permissions = ProjectPermission.objects.filter(
            user__email__in=emails,
            project=project,
            is_deleted=False,
        ).select_related("user")

        if permissions.count() != len(set(emails)):
            raise serializers.ValidationError(
                "Um ou mais destinatários não pertencem ao projeto"
            )

        invalid_recipients = [
            str(permission.uuid)
            for permission in permissions
            if not _is_eligible_recipient(permission)
        ]
        if invalid_recipients:
            raise serializers.ValidationError(
                "Apenas moderadores e visualizadores podem receber notificações"
            )

        attrs_permissions = list(permissions)
        self.context["recipient_permissions"] = attrs_permissions
        return recipients


def _is_eligible_recipient(permission: ProjectPermission) -> bool:
    return permission.is_admin or permission.sector_authorizations.exists()


def _can_configure_metric_goals(permission: ProjectPermission) -> bool:
    if permission.is_admin:
        return True
    return permission.sector_authorizations.filter(
        role=SectorAuthorization.ROLE_MANAGER
    ).exists()
