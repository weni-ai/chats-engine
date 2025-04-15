# Versão simples e confiável para chats/apps/projects/usecases/status_service.py

from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class InServiceStatusService:
    """
    Serviço simplificado para gerenciar o status 'In-Service' dos agentes.
    Usa o banco de dados como fonte primária da verdade.
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
    @transaction.atomic
    def room_assigned(cls, user, project):
        """
        Registra a atribuição de uma sala a um agente.
        Cria um status In-Service se for a primeira sala.
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
        
        # Verificar se já existe um status ativo
        status = CustomStatus.objects.select_for_update().filter(
            user=user,
            status_type=status_type,
            is_active=True,
            project=project
        ).first()
        
        if room_count >= 1:
            # Criar status se não existir e há salas
            if not status:
                CustomStatus.objects.create(
                    user=user,
                    status_type=status_type,
                    is_active=True,
                    project=project,
                    break_time=0
                )
                logger.info(f"Status In-Service criado para usuário {user.id} no projeto {project.id}")
    
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
    def schedule_sync_for_all_agents(cls):
        """
        Agenda sincronização periódica de todos os agentes ativos.
        Ideal para rodar como uma tarefa Celery agendada.
        """
        from chats.apps.rooms.models import Room
        from django.contrib.auth import get_user_model
        from django.db.models import Count
        from chats.apps.projects.models.models import Project
        
        User = get_user_model()
        
        # Encontrar todos os pares usuário-projeto com salas ativas
        active_agents = Room.objects.filter(
            is_active=True, 
            user__isnull=False
        ).values('user', 'queue__sector__project').annotate(
            count=Count('id')
        ).values_list('user', 'queue__sector__project').distinct()
        
        # Sincronizar cada agente
        for user_id, project_id in active_agents:
            try:
                with transaction.atomic():
                    cls.sync_agent_status(user_id, project_id)
            except Exception as e:
                logger.error(f"Erro ao sincronizar status: {e}")
    
    @classmethod
    @transaction.atomic
    def sync_agent_status(cls, user, project):
        """
        Sincroniza o status do agente com o estado real das salas.
        Útil para corrigir inconsistências.
        """
        from chats.apps.rooms.models import Room
        from chats.apps.projects.models.models import CustomStatus, Project
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Normalizar parâmetros
        if isinstance(user, (int, str)):
            user = User.objects.get(pk=user)
        if isinstance(project, (int, str)):
            project = Project.objects.get(pk=project)
            
        # Verificar com SELECT FOR UPDATE para evitar race conditions
        status_type = cls.get_or_create_status_type(project)
        
        # Obter o número de salas ativas atuais com bloqueio
        room_count = Room.objects.select_for_update().filter(
            user=user,
            queue__sector__project=project,
            is_active=True
        ).count()
        
        # Obter status atual
        status = CustomStatus.objects.select_for_update().filter(
            user=user,
            status_type=status_type,
            is_active=True,
            project=project
        ).first()
        
        # Corrigir inconsistências
        if room_count > 0 and not status:
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