from django.db.models import Count, OuterRef, Q, Subquery, F
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.projects.models import ProjectPermission

from django.db.models.functions import JSONObject
from django.contrib.postgres.aggregates import JSONBAgg
from django.contrib.postgres.fields import JSONField

from chats.apps.projects.models.models import CustomStatus

from .dto import Filters


class AgentRepository:
    def __init__(self):
        self.model = User.objects

    def get_agents_data(self, filters: Filters, project):
        tz = project.timezone
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        rooms_filter = {}
        closed_rooms = {}
        opened_rooms = {}

        agents_filters = Q(project_permissions__project=project) & Q(is_active=True)

        if filters.queue:
            # If filtering by queue, the agents list will include:
            # - Agents with authorization to the queue
            #   (even if they were never assigned to a room from the queue)
            # - Agents that are linked to rooms related to the queue
            #   (even if they don't have authorization to the queue anymore)

            rooms_filter["rooms__queue"] = filters.queue
            agents_filters &= Q(
                project_permissions__queue_authorizations__queue=filters.queue
            ) | Q(rooms__queue=filters.queue)

        elif filters.sector:
            # If filtering by sector, the agents list will include:
            # - Agents with authorization to the sector
            #   (even if they were never assigned to a room from the sector)
            # - Agents that are linked to rooms related to the sector
            #   (even if they don't have authorization to the sector anymore)
            print("filtro de setores", filters.sector)
            rooms_filter["rooms__queue__sector"] = filters.sector
            agents_filters &= Q(
                project_permissions__sector_authorizations__sector=filters.sector
            ) | Q(rooms__queue__sector=filters.sector)
        else:
            rooms_filter["rooms__queue__sector__project"] = project
        if filters.tag:
            rooms_filter["rooms__tags__in"] = filters.tag.split(",")
        if filters.start_date and filters.end_date:
            start_time = filters.start_date
            end_time = filters.end_date

            rooms_filter["rooms__created_on__range"] = [start_time, end_time]
            rooms_filter["rooms__is_active"] = False
            closed_rooms["rooms__ended_at__range"] = [start_time, end_time]
        else:
            closed_rooms["rooms__ended_at__gte"] = initial_datetime
            opened_rooms["rooms__is_active"] = True
            closed_rooms["rooms__is_active"] = False

        if filters.agent:
            rooms_filter["rooms__user"] = filters.agent

        project_permission_subquery = ProjectPermission.objects.filter(
            project_id=project,
            user_id=OuterRef("email"),
        ).values("status")[:1]

        agents_query = self.model
        if not filters.is_weni_admin:
            agents_query = agents_query.exclude(email__endswith="weni.ai")

        if filters.agent:
            agents_query = agents_query.filter(email=filters.agent)

        custom_status_subquery = Subquery(
            CustomStatus.objects.filter(
                user=OuterRef("email"),
                status_type__project=project,
            )
            .values("user")
            .annotate(
                aggregated=JSONBAgg(
                    JSONObject(
                        status_type=F("status_type__name"),
                        break_time=F("break_time"),
                        is_active=F("is_active")
                    )
                )
            )
            .values("aggregated"),
            output_field=JSONField(),
        )

        agents_query = (
            agents_query.filter(agents_filters)
            .annotate(
                status=Subquery(project_permission_subquery),
                closed=Count("rooms", filter=Q(**closed_rooms, **rooms_filter)),
                opened=Count("rooms", filter=Q(**opened_rooms, **rooms_filter)),
                custom_status=custom_status_subquery,
            )
            .distinct()
            .values(
                "first_name",
                "last_name",
                "email",
                "status",
                "closed",
                "opened",
                "custom_status",
            )
        )

        return agents_query

    def get_agents_custom_status(self, filters: Filters, project):
        tz = project.timezone
        initial_datetime = (
            timezone.now()
            .astimezone(tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )

        rooms_filter = {}
        closed_rooms = {}
        opened_rooms = {}

        if filters.queue:
            rooms_filter["rooms__queue"] = filters.queue
        elif filters.sector:
            rooms_filter["rooms__queue__sector"] = filters.sector
        else:
            rooms_filter["rooms__queue__sector__project"] = project

        if filters.tag:
            rooms_filter["rooms__tags__in"] = filters.tag.split(",")

        if filters.start_date and filters.end_date:
            start_time = filters.start_date
            end_time = filters.end_date
            rooms_filter["rooms__created_on__range"] = [start_time, end_time]
            rooms_filter["rooms__is_active"] = False
            closed_rooms["rooms__ended_at__range"] = [start_time, end_time]
        else:
            closed_rooms["rooms__ended_at__gte"] = initial_datetime
            opened_rooms["rooms__is_active"] = True
            closed_rooms["rooms__is_active"] = False

        if filters.agent:
            rooms_filter["rooms__user"] = filters.agent

        project_permission_queryset = ProjectPermission.objects.filter(
            project_id=project,
            user_id=OuterRef("email"),
        ).values("status")[:1]

        custom_status_subquery = Subquery(
            CustomStatus.objects.filter(
                user=OuterRef("email"),
                status_type__project=project,
            )
            .values("user")
            .annotate(
                aggregated=JSONBAgg(
                    JSONObject(
                        status_type=F("status_type__name"),
                        break_time=F("break_time"),
                        is_active=F("is_active")
                    )
                )
            )
            .values("aggregated"),
            output_field=JSONField(),
        )

        agents_query = self.model.all()

        if not filters.is_weni_admin:
            agents_query = agents_query.exclude(email__endswith="weni.ai")
        if filters.agent:
            agents_query = agents_query.filter(email=filters.agent)

        # Filtros para os agentes baseados na hierarquia setor -> fila
        agents_filter = {}
        
        # Caso 1: Tem fila e setor - filtra agentes que estão na fila específica que pertence ao setor
        if filters.queue and filters.sector:
            agents_filter["project_permissions__queue_authorizations__queue"] = filters.queue
            agents_filter["project_permissions__queue_authorizations__queue__sector"] = filters.sector
        # Caso 2: Tem apenas fila - filtra agentes que estão na fila específica
        elif filters.queue:
            agents_filter["project_permissions__queue_authorizations__queue"] = filters.queue
        # Caso 3: Tem apenas setor - filtra agentes que estão em qualquer fila do setor
        elif filters.sector:
            agents_filter["project_permissions__queue_authorizations__queue__sector"] = filters.sector

        # Aplica os filtros específicos de fila/setor, se houver
        if agents_filter:
            agents_query = agents_query.filter(**agents_filter).distinct()
            
        agents_query = (
            agents_query.filter(project_permissions__project=project, is_active=True)
            .annotate(
                status=Subquery(project_permission_queryset),
                closed=Count("rooms", filter=Q(**closed_rooms, **rooms_filter)),
                opened=Count("rooms", filter=Q(**opened_rooms, **rooms_filter)),
                custom_status=custom_status_subquery,
            )
            .values(
                "first_name",
                "last_name",
                "email",
                "status",
                "closed",
                "opened",
                "custom_status",
            )
        )

        return agents_query
