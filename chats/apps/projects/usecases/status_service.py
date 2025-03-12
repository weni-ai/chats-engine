from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from chats.apps.projects.models.models import CustomStatusType, CustomStatus

class InServiceStatusTracker:
    """Classe para rastrear o status 'In-Service' dos agentes"""
    
    STATUS_NAME = "In-Service"
    
    @staticmethod
    def get_cache_keys(user_id, project_id):
        """Retorna as chaves de cache para um agente"""
        return {
            "room_count": f"in_service_room_count:{user_id}:{project_id}",
            "status_id": f"in_service_status_id:{user_id}:{project_id}",
            "start_time": f"in_service_start_time:{user_id}:{project_id}"
        }
    
    @staticmethod
    def update_room_count(user, project, action="assigned"):
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
        
        keys = InServiceStatusTracker.get_cache_keys(user_id, project_id)
        
        if action == "assigned":
            # Incrementar o contador de salas de forma atômica
            new_count = cache.incr(keys["room_count"], 1)
            
            # Se é a primeira sala, criar um novo CustomStatus
            if new_count == 1:
                # Verificar se já existe um status ativo (para evitar duplicação)
                if not cache.get(keys["status_id"]):
                    with transaction.atomic():
                        # Obter ou criar o tipo de status
                        status_type, _ = CustomStatusType.objects.get_or_create(
                            name=InServiceStatusTracker.STATUS_NAME,
                            project=project,
                            defaults={"is_deleted": False}
                        )
                        
                        # Verificar se já existe um status ativo no banco
                        existing_status = CustomStatus.objects.filter(
                            user=user,
                            status_type=status_type,
                            is_active=True,
                            project=project
                        ).first()
                        
                        if existing_status:
                            custom_status = existing_status
                        else:
                            # Criar o CustomStatus ativo
                            custom_status = CustomStatus.objects.create(
                                user=user,
                                status_type=status_type,
                                is_active=True,
                                project=project,
                                break_time=0
                            )
                        
                        # Armazenar o ID do CustomStatus e o timestamp de início
                        cache.set(keys["status_id"], str(custom_status.uuid), 86400)
                        cache.set(keys["start_time"], timezone.now(), 86400)
        
        elif action == "closed":
            # Decrementar o contador de salas de forma atômica
            count = cache.get(keys["room_count"], 0)
            if count > 0:
                new_count = cache.decr(keys["room_count"], 1)
            else:
                new_count = 0
                cache.set(keys["room_count"], 0)
            
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
                        pass  # Status já foi finalizado por outro processo
                    
                    # Limpar os dados do cache
                    cache.delete(keys["status_id"])
                    cache.delete(keys["start_time"])