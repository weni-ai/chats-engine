import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

logger = logging.getLogger(__name__)


class InServiceStatusTracker:
    """Classe mantida para compatibilidade com código existente."""

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
    Serviço para gerenciar o status 'In-Service' dos agentes.
    Contabiliza o tempo de atendimento, pausando durante outros status.
    """

    STATUS_NAME = "In-Service"

    @classmethod
    def get_or_create_status_type(cls, project):
        """Obtém ou cria o tipo de status In-Service"""
        from chats.apps.projects.models.models import CustomStatusType

        status_type, created = CustomStatusType.objects.get_or_create(
            name=cls.STATUS_NAME,
            project=project,
            defaults={"is_deleted": False, "config": {"created_by_system": True}},
        )
        return status_type

    @classmethod
    def has_priority_status(cls, user, project):
        """Verifica se o usuário está em algum status que não seja In-Service"""
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
        Registra a atribuição de uma sala a um agente.
        Cria um status In-Service se for a primeira sala e não houver outro status ativo.
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

        has_priority = cls.has_priority_status(user, project)

        in_service_status = (
            CustomStatus.objects.select_for_update()
            .filter(user=user, status_type=status_type, is_active=True, project=project)
            .first()
        )

        # Verificar se o usuário está ONLINE
        from chats.apps.projects.models import ProjectPermission
        user_status = ProjectPermission.objects.get(user=user, project=project).status

        # Só criar In-Service se tem salas, não tem status ativo, não tem prioridade E está ONLINE
        if room_count >= 1 and not in_service_status and not has_priority and user_status == "ONLINE":
            CustomStatus.objects.create(
                user=user,
                status_type=status_type,
                is_active=True,
                project=project,
                break_time=0,
            )
            logger.info(
                f"Status In-Service criado para usuário {user.pk} no projeto {project.pk}"
            )

    @classmethod
    @transaction.atomic
    def room_closed(cls, user, project):
        """
        Registra o fechamento de uma sala.
        Finaliza o status In-Service se não houver mais salas.
        """
        from chats.apps.projects.models.models import CustomStatus
        from chats.apps.rooms.models import Room

        logger.info(f" DEBUG: room_closed chamado para user={user}, project={project}")

        if not user or not project:
            logger.info(f" DEBUG: room_closed retornando porque user ou project é None")
            return

        status_type = cls.get_or_create_status_type(project)

        room_count = (
            Room.objects.select_for_update()
            .filter(user=user, queue__sector__project=project, is_active=True)
            .count()
        )
        
        logger.info(f"DEBUG: room_count após fechar sala = {room_count}")

        if room_count == 0:
            status = (
                CustomStatus.objects.select_for_update()
                .filter(
                    user=user, status_type=status_type, is_active=True, project=project
                )
                .first()
            )

            if status:
                logger.info(f" DEBUG: Finalizando In-Service status")
                project_tz = project.timezone
                end_time = timezone.now().astimezone(project_tz)
                created_on = status.created_on.astimezone(project_tz)
                service_duration = end_time - created_on
                status.is_active = False
                status.break_time = int(service_duration.total_seconds())
                status.save(update_fields=["is_active", "break_time"])
                logger.info(f" DEBUG: In-Service finalizado com break_time = {status.break_time} seconds")
            else:
                logger.info(f"DEBUG: Não encontrou In-Service ativo para finalizar")
        else:
            logger.info(f"DEBUG: Ainda tem {room_count} salas ativas, não finaliza In-Service")

    @classmethod
    @transaction.atomic
    def sync_agent_status(cls, user, project):
        """
        Sincroniza o status do agente com o estado real das salas.
        Útil para corrigir inconsistências.
        """
        from chats.apps.projects.models.models import CustomStatus, Project
        from chats.apps.rooms.models import Room

        User = get_user_model()

        if isinstance(user, (int, str)):
            try:
                user = User.objects.get(pk=user)
            except User.DoesNotExist:
                logger.error(f"Usuário {user} não encontrado")
                return

        if isinstance(project, (int, str)):
            try:
                project = Project.objects.get(pk=project)
            except Project.DoesNotExist:
                logger.error(f"Projeto {project} não encontrado")
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
        Agenda sincronização periódica de todos os agentes ativos.
        Ideal para rodar como uma tarefa Celery agendada.
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
                logger.error(f"Erro ao sincronizar status: {e}")
