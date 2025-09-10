import json

import pendulum
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone
from django.apps import apps
from django.core.cache import cache

from chats.apps.projects.models import ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector
from .dto import EXCLUDED_DOMAINS


def get_export_data(project, filter):
    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    rooms_filter = {}

    if filter.get("start_date") and filter.get("end_date"):
        start_time = pendulum.parse(filter.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(filter.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )
        rooms_filter["created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
    else:
        rooms_filter["created_on__gte"] = initial_datetime

    if filter.get("agent"):
        rooms_filter["user"] = filter.get("agent")

    if filter.get("sector"):
        rooms_filter["queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["tags__name"] = filter.get("tag")
    else:
        rooms_filter["queue__sector__project"] = project

    export_data = Room.objects.filter(**rooms_filter).values_list(
        "metric__room__queue__name",
        "metric__waiting_time",
        "metric__message_response_time",
        "metric__interaction_time",
        "is_active",
    )

    return export_data


def get_general_data(project, filter):
    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    rooms_filter = {}

    rooms_filter_in_progress_chats = {}
    rooms_filter_in_progress_chats["user__isnull"] = False

    rooms_filter_waiting_service = {}
    rooms_filter_waiting_service["user__isnull"] = True
    rooms_filter_waiting_service["is_active"] = True

    rooms_filter_closed = {}
    rooms_filter_closed["is_active"] = False

    if filter.get("start_date") and filter.get("end_date"):
        start_time = pendulum.parse(filter.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(filter.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )
        rooms_filter["created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        rooms_filter_in_progress_chats["created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        rooms_filter_waiting_service["created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        rooms_filter_closed["ended_at__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        rooms_filter_in_progress_chats["is_active"] = False
    else:
        rooms_filter["created_on__gte"] = initial_datetime
        rooms_filter_in_progress_chats["is_active"] = True
        rooms_filter_closed["ended_at__gte"] = initial_datetime

    if filter.get("agent"):
        rooms_filter["user"] = filter.get("agent")
        rooms_filter_in_progress_chats["user"] = filter.get("agent")
        rooms_filter_closed["user"] = filter.get("agent")

    if filter.get("sector"):
        rooms_filter["queue__sector"] = filter.get("sector")
        rooms_filter_in_progress_chats["queue__sector"] = filter.get("sector")
        rooms_filter_waiting_service["queue__sector"] = filter.get("sector")
        rooms_filter_closed["queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["tags__name"] = filter.get("tag")
            rooms_filter_in_progress_chats["tags__name"] = filter.get("tag")
            rooms_filter_closed["tags__name"] = filter.get("tag")
    else:
        rooms_filter["queue__sector__project"] = project
        rooms_filter_in_progress_chats["queue__sector__project"] = project
        rooms_filter_waiting_service["queue__sector__project"] = project
        rooms_filter_closed["queue__sector__project"] = project

    data = {}
    metrics_rooms_count = Room.objects.filter(**rooms_filter).count()

    # in_progress
    active_chats = Room.objects.filter(**rooms_filter_in_progress_chats).count()

    # waiting_service
    queue_rooms = Room.objects.filter(**rooms_filter_waiting_service).count()

    # closed_rooms
    closed_rooms = Room.objects.filter(**rooms_filter_closed).count()

    # interaction_time
    interaction_value = Room.objects.filter(**rooms_filter).aggregate(
        interaction_time=Sum("metric__interaction_time")
    )
    if interaction_value and metrics_rooms_count > 0:
        interaction_time = interaction_value["interaction_time"] / metrics_rooms_count
    else:
        interaction_time = 0

    # response_time
    response_time_value = Room.objects.filter(**rooms_filter).aggregate(
        message_response_time=Sum("metric__message_response_time")
    )
    if response_time_value and metrics_rooms_count > 0:
        response_time = (
            response_time_value["message_response_time"] / metrics_rooms_count
        )
    else:
        response_time = 0

    # waiting_time
    waiting_time_value = Room.objects.filter(**rooms_filter).aggregate(
        waiting_time=Sum("metric__waiting_time")
    )
    if waiting_time_value and metrics_rooms_count > 0:
        waiting_time = waiting_time_value["waiting_time"] / metrics_rooms_count
    else:
        waiting_time = 0

    data = {
        "active_chats": active_chats,
        "queue_rooms": queue_rooms,
        "closed_rooms": closed_rooms,
        "interaction_time": interaction_time,
        "response_time": response_time,
        "waiting_time": waiting_time,
    }

    return data


def get_agents_data(project, filter):
    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    rooms_filter = {}
    closed_rooms = {}
    permission_filter = {"project": project}

    rooms_filter["user__rooms__is_active"] = True
    closed_rooms["user__rooms__is_active"] = False

    if filter.get("start_date") and filter.get("end_date"):
        start_time = pendulum.parse(filter.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(filter.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )
        rooms_filter["user__rooms__created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        closed_rooms["user__rooms__ended_at__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
    else:
        closed_rooms["user__rooms__ended_at__gte"] = initial_datetime

    if filter.get("agent"):
        rooms_filter["user"] = filter.get("agent")
        closed_rooms["user"] = filter.get("agent")

    if filter.get("sector"):
        rooms_filter["user__rooms__queue__sector"] = filter.get("sector")
        closed_rooms["user__rooms__queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["user__rooms__tags__name"] = filter.get("tag")
            closed_rooms["user__rooms__tags__name"] = filter.get("tag")
    else:
        rooms_filter["user__rooms__queue__sector__project"] = project
        closed_rooms["user__rooms__queue__sector__project"] = project

    # Criar filtro para excluir múltiplos domínios
    exclude_filter = Q()
    for domain in EXCLUDED_DOMAINS:
        exclude_filter |= Q(user__email__icontains=domain)

    queue_auth = (
        ProjectPermission.objects.filter(**permission_filter)
        .exclude(exclude_filter)
        .values(Name=F("user__first_name"))
        .annotate(
            opened_rooms=Count(
                "user__rooms",
                filter=Q(**rooms_filter),
                distinct=True,
            ),
            closed_rooms=Count(
                "user__rooms",
                filter=Q(**closed_rooms),
                distinct=True,
            ),
        )
    )

    data = json.dumps(list(queue_auth))
    return data


def get_sector_data(project, filter):
    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )

    model = Sector
    rooms_filter = {}
    model_filter = {"project": project}
    rooms_filter_prefix = "queues__"

    if filter.get("sector"):
        model = Queue
        rooms_filter_prefix = ""
        model_filter = {"sector": filter.get("sector")}
        rooms_filter["rooms__queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["rooms__tags__name"] = filter.get("tag")
        if filter.get("agent"):
            rooms_filter["rooms__user"] = filter.get("agent")
    else:
        rooms_filter[f"{rooms_filter_prefix}rooms__queue__sector__project"] = project
        if filter.get("agent"):
            rooms_filter[f"{rooms_filter_prefix}rooms__user"] = filter.get("agent")

    if filter.get("start_date") and filter.get("end_date"):
        start_time = pendulum.parse(filter.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(filter.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )
        rooms_filter[f"{rooms_filter_prefix}rooms__created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
    else:
        rooms_filter[f"{rooms_filter_prefix}rooms__created_on__gte"] = initial_datetime
    results = (
        model.objects.filter(**model_filter)
        .values(sector_name=F("name"))
        .annotate(
            waiting_time=Avg(
                f"{rooms_filter_prefix}rooms__metric__waiting_time",
                filter=Q(**rooms_filter),
            ),
            response_time=Avg(
                f"{rooms_filter_prefix}rooms__metric__message_response_time",
                filter=Q(**rooms_filter),
            ),
            interact_time=Avg(
                f"{rooms_filter_prefix}rooms__metric__interaction_time",
                filter=Q(**rooms_filter),
            ),
        )
    ).values("name", "waiting_time", "response_time", "interact_time")

    data = json.dumps(list(results))
    return data


class ModelFieldsPresenter:
    """
    Presenter para retornar os campos disponíveis dos principais models do sistema.
    """
    
    @staticmethod
    def _allowed_fields_map():
        """
        Campos permitidos por modelo, conforme especificação do cliente.
        Observações:
        - 'is_delete' => campo real 'is_deleted'
        - 'full_transfer_history' => campo real 'transfer_history'
        - 'service chat' => campo real 'service_chat'
        - 'is_wating' => campo real 'is_waiting'
        """
        return {
            'sectors': {
                'name', 'rooms_limit', 'config'
            },
            'queues': {
                'name', 'is_deleted', 'config'
            },
            'sector_tags': {
                'name'
            },
            'rooms': {
                'ended_at', 'ended_by', 'is_active', 'is_waiting',
                'urn', 'protocol', 'config', 'transfer_history',
                'service_chat', 'custom_fields', 'tags', 'contact', 'user'
            },
            'contacts': {
                'name', 'email', 'status', 'phone', 'custom_fields', 'external_id'
            },
            'users': {
                'email', 'first_name', 'last_name'
            },
        }

    @staticmethod
    def _filter_allowed(model_key, fields_dict):
        """
        Filtra o dicionário de campos baseado no mapa permitido.
        Mantém a estrutura {'field_name': {'type': ..., 'required': ...}}
        """
        allowed = ModelFieldsPresenter._allowed_fields_map().get(model_key, set())
        if not allowed:
            return {}
        return {k: v for k, v in fields_dict.items() if k in allowed}

    @staticmethod
    def get_models_info():
        """
        Return information about the fields of each model, with a 1 day cache.
        """
        cache_key = 'model_fields_presenter_models_info'
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
 
        raw_models_info = {
            'sectors': ModelFieldsPresenter._get_model_fields('sectors', 'Sector'),
            'queues': ModelFieldsPresenter._get_model_fields('queues', 'Queue'),
            'rooms': ModelFieldsPresenter._get_model_fields('rooms', 'Room'),
            'users': ModelFieldsPresenter._get_model_fields('accounts', 'User'),
            'sector_tags': ModelFieldsPresenter._get_model_fields('sectors', 'SectorTag'),
            'contacts': ModelFieldsPresenter._get_model_fields('contacts', 'Contact')
        }
        models_info = {
            key: ModelFieldsPresenter._filter_allowed(key, value)
            for key, value in raw_models_info.items()
        }
        cache.set(cache_key, models_info, timeout=86400)
        return models_info

    @staticmethod
    def _get_model_fields(app_label, model_name):
        """
        Return information about the fields of a specific model
        """
        try:
            model = apps.get_model(app_label, model_name)
            fields = {}
            
            for field in model._meta.get_fields():
                if hasattr(field, 'get_internal_type'):
                    field_info = {
                        'type': field.get_internal_type(),
                        'required': not field.null if hasattr(field, 'null') else True
                    }
                    
                    if field.get_internal_type() in ['ForeignKey', 'ManyToManyField']:
                        field_info['related_model'] = f"{field.related_model._meta.app_label}.{field.related_model._meta.model_name}"
                    
                    fields[field.name] = field_info

            return fields
        except LookupError:
            return {'error': f'Model {model_name} not found in app {app_label}'}