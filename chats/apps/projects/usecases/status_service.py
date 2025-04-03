from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from chats.apps.projects.models.models import CustomStatusType, CustomStatus, Project
from typing import Dict, Tuple, Optional, List
import logging
from django.contrib.auth import get_user_model

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
    def clear_cache(cls, user_id=None, project_id=None):
        """
        Limpa o cache relacionado ao InServiceStatusTracker
        
        Args:
            user_id: ID do usuário (opcional) - se fornecido, limpa apenas o cache deste usuário
            project_id: ID do projeto (opcional) - se fornecido junto com user_id, limpa apenas 
                        o cache específico deste usuário no projeto
        
        Se nenhum parâmetro for fornecido, limpa todo o cache do Django.
        """
        if user_id and project_id:
            # Limpar cache específico do usuário no projeto
            keys = cls.get_cache_keys(user_id, project_id)
            for key in keys.values():
                cache.delete(key)
            logger.info(f"Cache limpo para usuário {user_id} no projeto {project_id}")
        elif user_id:
            # Implementação simples que usa clear() geral
            # Uma implementação mais sofisticada buscaria todas as chaves deste usuário
            cache.clear()
            logger.info(f"Cache geral limpo ao tentar limpar para usuário {user_id}")
        else:
            # Limpar todo o cache
            cache.clear()
            logger.info("Todo o cache foi limpo")
    
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
    def get_cache_keys(cls, user_id, project_id):
        """
        Retorna as chaves de cache para um agente
        
        Args:
            user_id: ID do usuário ou objeto User
            project_id: ID do projeto ou objeto Project
        """
        # Normalizar as entradas (objeto → str)
        if hasattr(user_id, 'email'):
            user_id = user_id.email
        elif hasattr(user_id, 'pk'):
            user_id = user_id.pk
            
        if hasattr(project_id, 'name'):
            project_id = project_id.name
        elif hasattr(project_id, 'pk'):
            project_id = project_id.pk
            
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
        User = get_user_model()
        if isinstance(user, str):
            user_obj = User.objects.filter(email=user).first()
            if not user_obj:
                logger.warning(f"Usuário não encontrado para email: {user}")
                return None, False
            user = user_obj

        if isinstance(project, (int, str)):
            project_obj = Project.objects.filter(pk=project).first()
            if not project_obj:
                logger.warning(f"Projeto não encontrado para ID: {project}")
                return None, False
            project = project_obj

        user_id = user.pk
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
            logger.warning("Tentativa de atualizar contador para usuário nulo")
            return
            
        User = get_user_model()
        if isinstance(user, str):
            user_obj = User.objects.filter(email=user).first()
            if not user_obj:
                logger.warning(f"Usuário não encontrado para email: {user}")
                return
            user = user_obj

        if isinstance(project, (int, str)):
            project_obj = Project.objects.filter(pk=project).first()
            if not project_obj:
                logger.warning(f"Projeto não encontrado para ID: {project}")
                return
            project = project_obj

        user_id = user.pk
        project_id = project.pk
        
        keys = cls.get_cache_keys(user_id, project_id)
        timeout = cls.get_cache_timeout(project_id)
        
        logger.debug(f"Update room count: user={user_id}, project={project_id}, action={action}")
        logger.debug(f"Chaves geradas: {keys}")
        logger.debug(f"Contador antes: {cache.get(keys['room_count'], 0)}")
        
        try:
            if action == "assigned":
                # Garantir que a chave exista antes de incrementar
                if cache.get(keys["room_count"]) is None:
                    # Se o contador não existe mas deveria existir um status ativo, verificar o banco
                    status, _ = cls.get_current_status(user, project)
                    if status:
                        # Inicializar contador baseado no número atual de salas do agente no projeto
                        from chats.apps.rooms.models import Room
                        room_count = Room.objects.filter(
                            user=user, 
                            queue__sector__project=project, 
                            is_active=True
                        ).count()
                        
                        if room_count > 0:
                            logger.info(f"Recuperando contador para {user_id}:{project_id} - {room_count} salas ativas encontradas no banco")
                            # Incluir a sala atual no contador
                            cache.set(keys["room_count"], room_count, timeout)
                            # Garantir que as outras chaves também existam
                            cache.set(keys["status_id"], str(status.uuid), timeout)
                            cache.set(keys["start_time"], status.created_on, timeout)
                        else:
                            # Este é um caso extremo - há um status ativo mas nenhuma sala
                            # Inicializar com 0 para preparar para o incremento
                            logger.warning(f"Status ativo encontrado para {user_id}:{project_id} mas nenhuma sala ativa. Inicializando com 0.")
                            cache.set(keys["room_count"], 0, timeout)
                    else:
                        # Nenhum status ativo encontrado, inicializar contador com 0
                        cache.set(keys["room_count"], 0, timeout)
                
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
                
                # Após incrementar
                logger.debug(f"Contador depois: {cache.get(keys['room_count'], 0)}")
                
            elif action == "closed":
                # Verificar se as chaves de cache existem
                current_count = cache.get(keys["room_count"])
                
                # Se o contador não existe no cache, verificar se existe um status ativo no banco
                if current_count is None:
                    # Verificar se existem salas ativas para este agente no projeto
                    from chats.apps.rooms.models import Room
                    room_count = Room.objects.filter(
                        user=user, 
                        queue__sector__project=project, 
                        is_active=True
                    ).count()
                    
                    # Verificar também se existe um status ativo
                    status, _ = cls.get_current_status(user, project)
                    
                    if status:
                        # Existe um status ativo no banco
                        if room_count > 0:
                            # Há salas ativas, inicializar o contador com o valor real
                            # Não adicionamos +1 pois a sala que está sendo fechada já está incluída no room_count
                            logger.warning(f"Status ativo encontrado para {user_id}:{project_id} sem contador no cache. Inicializando com {room_count} salas.")
                            cache.set(keys["room_count"], room_count, timeout)
                            cache.set(keys["status_id"], str(status.uuid), timeout)
                            cache.set(keys["start_time"], status.created_on, timeout)
                            current_count = room_count
                        else:
                            # Não há salas ativas, mas existe um status ativo
                            # Definir contador como 1 para que possa ser decrementado para 0
                            logger.warning(f"Status ativo encontrado para {user_id}:{project_id} mas nenhuma sala ativa no banco. Inicializando com 1.")
                            cache.set(keys["room_count"], 1, timeout)
                            cache.set(keys["status_id"], str(status.uuid), timeout)
                            cache.set(keys["start_time"], status.created_on, timeout)
                            current_count = 1
                    else:
                        # Não existe status ativo
                        if room_count > 0:
                            # Caso extremo: há salas ativas mas nenhum status ativo
                            # Criar um status temporário e definir contador igual ao número de salas
                            logger.warning(f"Nenhum status ativo encontrado para {user_id}:{project_id} mas {room_count} salas ativas. Criando status e inicializando contador.")
                            
                            # Criar um novo status
                            with transaction.atomic():
                                status_type = cls.get_or_create_status_type(project)
                                new_status = CustomStatus.objects.create(
                                    user=user,
                                    status_type=status_type,
                                    is_active=True,
                                    project=project,
                                    break_time=0
                                )
                                
                                cache.set(keys["room_count"], room_count, timeout)
                                cache.set(keys["status_id"], str(new_status.uuid), timeout)
                                cache.set(keys["start_time"], timezone.now(), timeout)
                                current_count = room_count
                        else:
                            # Não há status ativo nem salas ativas - situação normal
                            logger.info(f"Tentativa de fechar sala para {user_id}:{project_id} sem contador no cache nem status ativo. Definindo como 0.")
                            cache.set(keys["room_count"], 0, timeout)
                            current_count = 0
                
                # Decrementar o contador (com proteção para não ficar negativo)
                if current_count > 0:
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
                                logger.info(f"Status finalizado para {user_id}:{project_id}, duração: {service_duration}")
                        
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
                    else:
                        # Verificar se existe um status ativo no banco que não está no cache
                        status, _ = cls.get_current_status(user, project)
                        if status:
                            try:
                                with transaction.atomic():
                                    # Finalizar o status
                                    status.is_active = False
                                    # Usar o created_on como substituto para o start_time
                                    service_duration = timezone.now() - status.created_on
                                    status.break_time = int(service_duration.total_seconds())
                                    status.save(update_fields=['is_active', 'break_time'])
                                    logger.info(f"Status ativo encontrado no banco para {user_id}:{project_id} sem entradas no cache. Finalizado.")
                            except Exception as e:
                                logger.error(f"Erro ao finalizar status do banco sem cache: {e}")
            
            else:
                logger.warning(f"Ação desconhecida: {action}")
                
        except Exception as e:
            logger.error(f"Erro ao atualizar contagem de salas: {e}")