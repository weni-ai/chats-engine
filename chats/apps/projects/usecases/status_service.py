import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

logger = logging.getLogger(__name__)


class InServiceStatusTracker:
    @classmethod
    def room_assigned(cls, user, project):
        return InServiceStatusService.room_assigned(user, project)

    @classmethod
    def room_closed(cls, user, project):
        return InServiceStatusService.room_closed(user, project)

    @classmethod
    def sync_agent_status(cls, user, project):
        return InServiceStatusService.sync_agent_status(user, project)


class InServiceStatusService:
    """
    Service to manage agents' 'In-Service' status.
    Tracks service time, pausing during other statuses.
    """

    STATUS_NAME = "In-Service"

    @classmethod
    def get_or_create_status_type(cls, project):
        """Gets or creates the In-Service status type"""
        from chats.apps.projects.models.models import CustomStatusType

        status_type, created = CustomStatusType.objects.get_or_create(
            name=cls.STATUS_NAME,
            project=project,
            defaults={"is_deleted": False, "config": {"created_by_system": True}},
        )
        return status_type

    @classmethod
    def has_priority_status(cls, user, project):
        """Checks if the user has any status other than In-Service"""
        from chats.apps.projects.models.models import CustomStatus

        in_service_type = cls.get_or_create_status_type(project)

        return (
            CustomStatus.objects.filter(user=user, project=project, is_active=True)
            .exclude(status_type=in_service_type)
            .exists()
        )

    @classmethod
    @transaction.atomic
    def room_assigned(cls, user, project):
        """
        Records a room assignment to an agent.
        Creates an In-Service status if it's the first room and there's no other active status.
        """
        from chats.apps.projects.models import ProjectPermission
        from chats.apps.projects.models.models import CustomStatus
        from chats.apps.rooms.models import Room

        if not user or not project:
            return

        permission = ProjectPermission.objects.filter(
            user=user, project=project
        ).first()

        if not permission:
            return

        user_status = permission.status

        status_type = cls.get_or_create_status_type(project)

        room_count = (
            Room.objects.select_for_update()
            .filter(user=user, queue__sector__project=project, is_active=True)
            .count()
        )

        has_priority = cls.has_priority_status(user, project)

        in_service_status = (
            CustomStatus.objects.select_for_update()
            .filter(user=user, status_type=status_type, is_active=True, project=project)
            .first()
        )

        if (
            room_count >= 1
            and not in_service_status
            and not has_priority
            and user_status == "ONLINE"
        ):
            CustomStatus.objects.create(
                user=user,
                status_type=status_type,
                is_active=True,
                project=project,
                break_time=0,
            )
            logger.info(
                f"Status In-Service created for user {user.pk} in project {project.pk}"
            )

    @classmethod
    @transaction.atomic
    def room_closed(cls, user, project):
        """
        Records a room closure.
        Ends the In-Service status if there are no more rooms.
        """
        from chats.apps.projects.models.models import CustomStatus
        from chats.apps.rooms.models import Room

        if not user or not project:
            return

        status_type = cls.get_or_create_status_type(project)

        room_count = (
            Room.objects.select_for_update()
            .filter(user=user, queue__sector__project=project, is_active=True)
            .count()
        )

        if room_count == 0:
            status = (
                CustomStatus.objects.select_for_update()
                .filter(
                    user=user, status_type=status_type, is_active=True, project=project
                )
                .first()
            )

            if status:
                project_tz = project.timezone
                end_time = timezone.now().astimezone(project_tz)
                created_on = status.created_on.astimezone(project_tz)
                service_duration = end_time - created_on
                status.is_active = False
                status.break_time = int(service_duration.total_seconds())
                status.save(update_fields=["is_active", "break_time"])
            else:
                logger.info("room_closed: Não encontrou In-Service ativo")
        else:
            logger.info(f"room_closed: Ainda tem {room_count} salas ativas")

    @classmethod
    @transaction.atomic
    def sync_agent_status(cls, user, project):
        """
        Synchronizes the agent's status with the actual state of their rooms.
        Useful for fixing inconsistencies.
        """
        from chats.apps.projects.models.models import CustomStatus, Project
        from chats.apps.rooms.models import Room

        User = get_user_model()

        if isinstance(user, (int, str)):
            try:
                user = User.objects.get(pk=user)
            except User.DoesNotExist:
                logger.info(f"Usuário {user} não encontrado")
                return

        if isinstance(project, (int, str)):
            try:
                project = Project.objects.get(pk=project)
            except Project.DoesNotExist:
                logger.info(f"Projeto {project} não encontrado")
                return

        status_type = cls.get_or_create_status_type(project)

        room_count = (
            Room.objects.select_for_update()
            .filter(user=user, queue__sector__project=project, is_active=True)
            .count()
        )

        has_priority = cls.has_priority_status(user, project)

        status = (
            CustomStatus.objects.select_for_update()
            .filter(user=user, status_type=status_type, is_active=True, project=project)
            .first()
        )

        if room_count > 0 and not status and not has_priority:
            CustomStatus.objects.create(
                user=user,
                status_type=status_type,
                is_active=True,
                project=project,
                break_time=0,
            )
            logger.info(
                f"Status In-Service criado durante sincronização para usuário {user.pk} no projeto {project.pk}"
            )
        elif room_count == 0 and status:
            project_tz = project.timezone
            end_time = timezone.now().astimezone(project_tz)
            created_on = status.created_on.astimezone(project_tz)
            service_duration = end_time - created_on
            status.is_active = False
            status.break_time = int(service_duration.total_seconds())
            status.save(update_fields=["is_active", "break_time"])
            logger.info(
                f"Status In-Service finalizado durante sincronização para usuário {user.pk} no projeto {project.pk}"
            )

    @classmethod
    def schedule_sync_for_all_agents(cls):
        """
        Schedules periodic synchronization for all active agents.
        Ideal to run as a scheduled Celery task.
        """
        from chats.apps.rooms.models import Room

        active_agents = (
            Room.objects.filter(is_active=True, user__isnull=False)
            .values("user", "queue__sector__project")
            .annotate(count=Count("pk"))
            .values_list("user", "queue__sector__project")
            .distinct()
        )

        for user_id, project_id in active_agents:
            try:
                with transaction.atomic():
                    cls.sync_agent_status(user_id, project_id)
            except Exception as e:
                logger.info(f"Erro ao sincronizar status: {e}")
