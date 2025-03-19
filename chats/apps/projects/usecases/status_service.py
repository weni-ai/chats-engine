from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from chats.apps.projects.models.models import CustomStatusType, CustomStatus
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class InServiceStatusTracker:
    """Classe para rastrear o status 'In-Service' dos agentes"""
    
    STATUS_NAME = "In-Service"
    CACHE_TIMEOUT = 86400  # 24 horas em segundos
    
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
        project_id = project.id
        keys = cls.get_cache_keys(user_id, project_id)
        
        # Tentar obter do cache primeiro
        status_id = cache.get(keys["status_id"])
        if status_id:
            try:
                status = CustomStatus.objects.get(uuid=status_id, is_active=True)
                return status, True
            except CustomStatus.DoesNotExist:
                # Status no cache não existe mais no banco, limpar cache
                cache.delete(keys["status_id"])
                cache.delete(keys["start_time"])
        
        # Verificar no banco de dados
        status_type = cls.get_or_create_status_type(project)
        status = CustomStatus.objects.filter(
            user=user,
            status_type=status_type,
            is_active=True,
            project=project
        ).first()
        
        # Se encontrou no banco mas não estava no cache, atualizar cache
        if status:
            cache.set(keys["status_id"], str(status.uuid), cls.CACHE_TIMEOUT)
            # Não temos o start_time original, usar o created_on do status
            cache.set(keys["start_time"], status.created_on, cls.CACHE_TIMEOUT)
            
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
        project_id = project.id
        
        keys = cls.get_cache_keys(user_id, project_id)
        
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
                            
                            # Atualizar cache
                            cache.set(keys["status_id"], str(status.uuid), cls.CACHE_TIMEOUT)
                            cache.set(keys["start_time"], timezone.now(), cls.CACHE_TIMEOUT)
                
            elif action == "closed":
                # Obter contagem atual (com fallback para 0)
                count = cache.get(keys["room_count"], 0)
                
                # Decrementar o contador (com proteção para não ficar negativo)
                if count > 0:
                    new_count = cache.decr(keys["room_count"], 1)
                else:
                    new_count = 0
                    cache.set(keys["room_count"], 0, cls.CACHE_TIMEOUT)
                
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
                                custom_status.save()
                        
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