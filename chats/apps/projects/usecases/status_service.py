from django.db import transaction
from django.utils import timezone
import logging
from chats.apps.projects.models.models import CustomStatus
from django.contrib.auth import get_user_model
from django.db.models import Count
from chats.apps.projects.models.models import Project

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
            defaults={"is_deleted": False, "config": {"created_by_system": True}}
        )
        return status_type
    
    @classmethod
    def has_priority_status(cls, user, project):
        """Verifica se o usuário está em algum status que não seja In-Service"""
        from chats.apps.projects.models.models import CustomStatus
        
        # Obter o tipo de status In-Service
        in_service_type = cls.get_or_create_status_type(project)
        
        # Verificar se existe qualquer outro status ativo que não seja In-Service
        return CustomStatus.objects.filter(
            user=user,
            project=project,
            is_active=True
        ).exclude(
            status_type=in_service_type
        ).exists()
    
    @classmethod
    @transaction.atomic
    def room_assigned(cls, user, project):
        """
        Registra a atribuição de uma sala a um agente.
        Cria um status In-Service se for a primeira sala e não houver outro status ativo.
        """
        from chats.apps.rooms.models import Room
        from chats.apps.projects.models.models import CustomStatus
        
        if not user or not project:
            return
            
        # Verificar com SELECT FOR UPDATE para evitar race conditions
        status_type = cls.get_or_create_status_type(project)
        
        # Obter o número de salas ativas atuais com bloqueio
        room_count = Room.objects.select_for_update().filter(
            user=user,
            queue__sector__project=project,
            is_active=True
        ).count()
        
        # Verificar se usuário está em status de maior prioridade
        has_priority = cls.has_priority_status(user, project)
        
        # Verificar se já existe um status ativo
        in_service_status = CustomStatus.objects.select_for_update().filter(
            user=user,
            status_type=status_type,
            is_active=True,
            project=project
        ).first()
        
        if room_count >= 1:
            if not in_service_status and not has_priority:
                # Criar novo status apenas se não tiver status de maior prioridade
                CustomStatus.objects.create(
                    user=user,
                    status_type=status_type,
                    is_active=True,
                    project=project,
                    break_time=0
                )
                logger.info(f"Status In-Service criado para usuário {user.pk} no projeto {project.pk}")
    
    @classmethod
    @transaction.atomic
    def room_closed(cls, user, project):
        """
        Registra o fechamento de uma sala.
        Finaliza o status In-Service se não houver mais salas.
        """
        from chats.apps.rooms.models import Room
        from chats.apps.projects.models.models import CustomStatus
        
        if not user or not project:
            return
            
        # Verificar com SELECT FOR UPDATE para evitar race conditions
        status_type = cls.get_or_create_status_type(project)
        
        # Obter o número de salas ativas atuais com bloqueio
        room_count = Room.objects.select_for_update().filter(
            user=user,
            queue__sector__project=project,
            is_active=True
        ).count()
        
        # Se não há mais salas, finalizar o status
        if room_count == 0:
            status = CustomStatus.objects.select_for_update().filter(
                user=user,
                status_type=status_type,
                is_active=True,
                project=project
            ).first()
            
            if status:
                # Calcular duração e finalizar status
                service_duration = timezone.now() - status.created_on
                status.is_active = False
                status.break_time = int(service_duration.total_seconds())
                status.save(update_fields=['is_active', 'break_time'])
                logger.info(f"Status In-Service finalizado para usuário {user.pk} no projeto {project.pk}")

    @classmethod
    def handle_status_change(cls, user, project, status_type, is_active):
        """
        Gerencia mudanças de status - quando um agente entra ou sai de qualquer status
        
        Args:
            user: O usuário que mudou de status
            project: O projeto associado
            status_type: O tipo de status alterado
            is_active: Se o status foi ativado (True) ou desativado (False)
        """
        from chats.apps.rooms.models import Room
        from chats.apps.projects.models.models import CustomStatus
        
        # Obter o tipo de status In-Service
        in_service_type = cls.get_or_create_status_type(project)
        
        # Ignorar mudanças no próprio status In-Service
        if status_type.pk == in_service_type.pk:
            return
            
        # Verificar com SELECT FOR UPDATE para evitar race conditions
        with transaction.atomic():
            # Verificar salas ativas
            room_count = Room.objects.select_for_update().filter(
                user=user,
                queue__sector__project=project,
                is_active=True
            ).count()
            
            # Status In-Service atual
            in_service_status = CustomStatus.objects.select_for_update().filter(
                user=user,
                status_type=in_service_type,
                is_active=True,
                project=project
            ).first()
            
            if is_active:
                # Se qualquer outro status foi ativado, pausar o In-Service
                if in_service_status:
                    service_duration = timezone.now() - in_service_status.created_on
                    in_service_status.is_active = False
                    in_service_status.break_time += int(service_duration.total_seconds())
                    in_service_status.save(update_fields=['is_active', 'break_time'])
                    logger.info(f"Status In-Service pausado devido a outro status para usuário {user.pk}")
            else:
                # Se um status foi desativado, verificar se tem outras prioridades
                has_other_priority = cls.has_priority_status(user, project)
                
                # Se não tem outros status ativos e tem salas, reativar In-Service
                if not has_other_priority and room_count > 0:
                    CustomStatus.objects.create(
                        user=user,
                        status_type=in_service_type,
                        is_active=True,
                        project=project,
                        break_time=0
                    )
                    logger.info(f"Status In-Service recriado após fim de outro status para usuário {user.pk}")
    
    @classmethod
    @transaction.atomic
    def sync_agent_status(cls, user, project):
        """
        Sincroniza o status do agente com o estado real das salas.
        Útil para corrigir inconsistências.
        """
        from chats.apps.rooms.models import Room
        from chats.apps.projects.models.models import CustomStatus, Project
        
        User = get_user_model()
        
        # Normalizar parâmetros
        if isinstance(user, (int, str)):
            try:
                user = User.objects.get(pk=user)
            except User.DoesNotExist:
                logger.error(f"Usuário {user} não encontrado")
                return
                
        if isinstance(project, (int, str)):
            try:
                from chats.apps.projects.models.models import Project
                project = Project.objects.get(pk=project)
            except Project.DoesNotExist:
                logger.error(f"Projeto {project} não encontrado")
                return
            
        # Verificar com SELECT FOR UPDATE para evitar race conditions
        status_type = cls.get_or_create_status_type(project)
        
        # Obter o número de salas ativas atuais com bloqueio
        room_count = Room.objects.select_for_update().filter(
            user=user,
            queue__sector__project=project,
            is_active=True
        ).count()
        
        # Verificar se usuário está em status de maior prioridade
        has_priority = cls.has_priority_status(user, project)
        
        # Obter status atual
        status = CustomStatus.objects.select_for_update().filter(
            user=user,
            status_type=status_type,
            is_active=True,
            project=project
        ).first()
        
        # Corrigir inconsistências
        if room_count > 0 and not status and not has_priority:
            # Deveria haver um status ativo, criar um novo
            CustomStatus.objects.create(
                user=user,
                status_type=status_type,
                is_active=True,
                project=project,
                break_time=0
            )
            logger.info(f"Status In-Service criado durante sincronização para usuário {user.pk} no projeto {project.pk}")
        elif room_count == 0 and status:
            # Não deveria haver status ativo, finalizar
            service_duration = timezone.now() - status.created_on
            status.is_active = False
            status.break_time = int(service_duration.total_seconds())
            status.save(update_fields=['is_active', 'break_time'])
            logger.info(f"Status In-Service finalizado durante sincronização para usuário {user.pk} no projeto {project.pk}")

    @classmethod
    def schedule_sync_for_all_agents(cls):
        """
        Agenda sincronização periódica de todos os agentes ativos.
        Ideal para rodar como uma tarefa Celery agendada.
        """
        from chats.apps.rooms.models import Room
        
        # Encontrar todos os pares usuário-projeto com salas ativas
        active_agents = Room.objects.filter(
            is_active=True, 
            user__isnull=False
        ).values('user', 'queue__sector__project').annotate(
            count=Count('pk')
        ).values_list('user', 'queue__sector__project').distinct()
        
        # Sincronizar cada agente
        for user_id, project_id in active_agents:
            try:
                with transaction.atomic():
                    cls.sync_agent_status(user_id, project_id)
            except Exception as e:
                logger.error(f"Erro ao sincronizar status: {e}")