from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from chats.apps.projects.models.models import CustomStatusType, CustomStatus
from typing import Dict, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)

class InServiceStatusTracker:
    """Classe para rastrear o status 'In-Service' dos agentes"""
    
    STATUS_NAME = "In-Service"
    DEFAULT_CACHE_TIMEOUT = 86400    # 1 dia em segundos (padrão)
    EXTENDED_CACHE_TIMEOUT = 259200  # 3 dias em segundos
    
    # Lista de project_ids que devem usar o timeout padrão de 1 dia
    # Todos os outros projetos usarão o timeout estendido de 3 dias
    DEFAULT_TIMEOUT_PROJECTS = [
        # Lista de IDs de projetos que devem usar o timeout padrão
        # Exemplo: 1, 2, 3
    ]
    
    @classmethod
    def get_cache_timeout(cls, project_id: int) -> int:
        """
        Retorna o timeout apropriado para o projeto
        
        Args:
            project_id: ID do projeto
            
        Returns:
            Tempo de cache em segundos (1 dia ou 3 dias)
        """
        if project_id in cls.DEFAULT_TIMEOUT_PROJECTS:
            return cls.DEFAULT_CACHE_TIMEOUT
        return cls.EXTENDED_CACHE_TIMEOUT
    
    @classmethod
    def get_cache_keys(cls, user_id: int, project_id: int) -> Dict[str, str]:
        """
        Retorna as chaves de cache para um agente
        
        Args:
            user_id: ID do usuário
            project_id: ID do projeto
            
        Returns:
            Dict com as chaves de cache
        """
        return {
            "room_count": f"in_service_room_count:{user_id}:{project_id}",
            "status_id": f"in_service_status_id:{user_id}:{project_id}",
            "start_time": f"in_service_start_time:{user_id}:{project_id}"
        }
    
    @classmethod
    def get_or_create_status_type(cls, project) -> CustomStatusType:
        """
        Obtém ou cria o tipo de status In-Service
        
        Args:
            project: O projeto atual
            
        Returns:
            O objeto CustomStatusType
        """
        status_type, created = CustomStatusType.objects.get_or_create(
            name=cls.STATUS_NAME,
            project=project,
            defaults={"is_deleted": False, "config": {"created_by_system": True}}
        )
        
        return status_type
    
    @classmethod
    def _get_status_from_cache(cls, user_id, project_id):
        """
        Tenta recuperar o status do cache
        
        Args:
            user_id: ID do usuário
            project_id: ID do projeto
            
        Returns:
            Tupla com (status_obj, encontrado) ou (None, False) se não encontrado
        """
        keys = cls.get_cache_keys(user_id, project_id)
        status_id = cache.get(keys["status_id"])
        
        if not status_id:
            return None, False
            
        try:
            status = CustomStatus.objects.get(uuid=status_id, is_active=True)
            return status, True
        except CustomStatus.DoesNotExist:
            # Status no cache não existe mais no banco, limpar cache
            cache.delete(keys["status_id"])
            cache.delete(keys["start_time"])
            return None, False

    @classmethod
    def _get_status_from_db(cls, user, project):
        """
        Busca o status ativo no banco de dados
        
        Args:
            user: O usuário agente
            project: O projeto atual
            
        Returns:
            Objeto CustomStatus ou None se não encontrado
        """
        status_type = cls.get_or_create_status_type(project)
        return CustomStatus.objects.filter(
            user=user,
            status_type=status_type,
            is_active=True,
            project=project
        ).first()

    @classmethod
    def _update_status_cache(cls, user_id, project_id, status):
        """
        Atualiza o cache com as informações do status encontrado no banco
        
        Args:
            user_id: ID do usuário
            project_id: ID do projeto
            status: Objeto CustomStatus
        """
        keys = cls.get_cache_keys(user_id, project_id)
        timeout = cls.get_cache_timeout(project_id)
        
        cache.set(keys["status_id"], str(status.uuid), timeout)
        # Não temos o start_time original, usar o created_on do status
        cache.set(keys["start_time"], status.created_on, timeout)

    @classmethod
    def get_current_status(cls, user, project) -> Tuple[Optional[CustomStatus], bool]:
        """
        Obtém o status atual do cache ou banco de dados
        
        Args:
            user: O usuário agente
            project: O projeto atual
            
        Returns:
            Tupla com (status_obj, from_cache)
        """
        user_id = user.id
        project_id = project.pk
        
        # Tentar obter do cache primeiro
        status, from_cache = cls._get_status_from_cache(user_id, project_id)
        if status:
            return status, from_cache
        
        # Verificar no banco de dados
        status = cls._get_status_from_db(user, project)
        
        # Se encontrou no banco mas não estava no cache, atualizar cache
        if status:
            cls._update_status_cache(user_id, project_id, status)
            
        return status, False
    
    @classmethod
    def update_room_count(cls, user, project, action="assigned") -> None:
        """
        Atualiza o contador de salas e o status In-Service do agente
        
        Args:
            user: O usuário agente
            project: O projeto atual
            action: "assigned" quando uma sala é atribuída, "closed" quando fechada
        """
        if not user:
            return
            
        user_id = user.id
        project_id = project.pk
        
        keys = cls.get_cache_keys(user_id, project_id)
        timeout = cls.get_cache_timeout(project_id)
        
        try:
            if action == "assigned":
                # Incrementar o contador de salas de forma atômica
                new_count = cache.incr(keys["room_count"], 1)
                
                # Se é a primeira sala, criar um novo CustomStatus
                if new_count == 1:
                    with transaction.atomic():
                        # Verificar se já existe um status ativo
                        status, from_cache = cls.get_current_status(user, project)
                        
                        if not status:
                            # Criar novo status
                            status_type = cls.get_or_create_status_type(project)
                            status = CustomStatus.objects.create(
                                user=user,
                                status_type=status_type,
                                is_active=True,
                                project=project,
                                break_time=0
                            )
                            
                            # Atualizar cache com o timeout apropriado para este projeto
                            cache.set(keys["status_id"], str(status.uuid), timeout)
                            cache.set(keys["start_time"], timezone.now(), timeout)
                
            elif action == "closed":
                # Obter contagem atual (com fallback para 0)
                count = cache.get(keys["room_count"], 0)
                
                # Decrementar o contador (com proteção para não ficar negativo)
                if count > 0:
                    new_count = cache.decr(keys["room_count"], 1)
                else:
                    new_count = 0
                    cache.set(keys["room_count"], 0, timeout)
                
                # Se não tem mais salas ativas, finalizar o CustomStatus
                if new_count == 0:
                    status_id = cache.get(keys["status_id"])
                    start_time = cache.get(keys["start_time"])
                    
                    if status_id and start_time:
                        try:
                            with transaction.atomic():
                                # Buscar o CustomStatus ativo
                                custom_status = CustomStatus.objects.select_for_update().get(
                                    uuid=status_id,
                                    is_active=True
                                )
                                
                                # Calcular a duração do serviço
                                service_duration = timezone.now() - start_time
                                
                                # Atualizar e finalizar o CustomStatus
                                custom_status.is_active = False
                                custom_status.break_time = int(service_duration.total_seconds())
                                custom_status.save(update_fields=['is_active', 'break_time'])
                        
                        except CustomStatus.DoesNotExist:
                            logger.warning(
                                f"Tentativa de finalizar CustomStatus inexistente: {status_id}"
                            )
                        except Exception as e:
                            logger.error(f"Erro ao finalizar CustomStatus: {e}")
                        finally:
                            # Limpar os dados do cache mesmo se ocorrer erro
                            cache.delete(keys["status_id"])
                            cache.delete(keys["start_time"])
                
        except Exception as e:
            logger.error(f"Erro ao atualizar contagem de salas: {e}")