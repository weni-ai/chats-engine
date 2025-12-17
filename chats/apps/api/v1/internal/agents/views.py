from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.apps.api.v1.internal.agents.utils import validate_agent_disconnect
from chats.apps.api.v1.permissions import ProjectBodyIsAdmin
from chats.apps.projects.models import CustomStatus, ProjectPermission
from chats.apps.projects.tasks import create_agent_disconnect_log
from chats.utils.websockets import send_channels_group


class AgentDisconnectView(APIView):
    swagger_tag = "Agents"
    permission_classes = [permissions.IsAuthenticated, ProjectBodyIsAdmin]

    def post(self, request):
        project_uuid = request.data.get("project_uuid")
        agent_email = request.data.get("agent") or request.data.get("agent_email")

        project, target_user, target_perm = validate_agent_disconnect(
            request.user, project_uuid, agent_email
        )

        with transaction.atomic():
            active_qs = CustomStatus.objects.select_for_update().filter(
                user=target_user,
                project=project,
                is_active=True,
                status_type__config__created_by_system__isnull=True,
            )
            statuses = list(active_qs)
            closed_count = active_qs.update(is_active=False)
            if statuses:
                end_time = timezone.now()
                project_tz = project.timezone
                for custom_status in statuses:
                    local_created_on = custom_status.created_on.astimezone(project_tz)
                    local_end_time = end_time.astimezone(project_tz)
                    custom_status.break_time = int(
                        (local_end_time - local_created_on).total_seconds()
                    )
                    custom_status.save(update_fields=["break_time"])

            if closed_count > 0:
                permission_pk = target_perm.pk
                user_email = target_user.email
                disconnected_by_email = request.user.email

                transaction.on_commit(
                    lambda: send_channels_group(
                        group_name=f"permission_{permission_pk}",
                        call_type="notify",
                        content={
                            "user": user_email,
                            "custom_status_active": False,
                            "user_disconnected_agent": disconnected_by_email,
                        },
                        action="custom_status.close",
                    )
                )
                transaction.on_commit(
                    lambda: create_agent_disconnect_log.delay(
                        str(project.uuid), target_user.email, request.user.email
                    )
                    if getattr(settings, "USE_CELERY", False)
                    else create_agent_disconnect_log(
                        str(project.uuid), target_user.email, request.user.email
                    )
                )
                return Response(status=status.HTTP_200_OK)

            if target_perm.status != ProjectPermission.STATUS_OFFLINE:
                target_perm.status = ProjectPermission.STATUS_OFFLINE
                target_perm.save(update_fields=["status"])

            transaction.on_commit(
                lambda: send_channels_group(
                    group_name=f"permission_{target_perm.pk}",
                    call_type="notify",
                    content={
                        "user": target_user.email,
                        "status": ProjectPermission.STATUS_OFFLINE,
                        "user_disconnected_agent": request.user.email,
                    },
                    action="status.close",
                )
            )
            transaction.on_commit(
                lambda: create_agent_disconnect_log.delay(
                    str(project.uuid), target_user.email, request.user.email
                )
                if getattr(settings, "USE_CELERY", False)
                else create_agent_disconnect_log(
                    str(project.uuid), target_user.email, request.user.email
                )
            )
            return Response(status=status.HTTP_200_OK)
