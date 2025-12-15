from datetime import datetime

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.api.v1.permissions import (
    HasAgentPermissionAnyQueueSector,
    IsProjectAdmin,
    IsSectorManager,
)
from chats.apps.api.v1.sectors import serializers as sector_serializers
from chats.apps.api.v1.sectors.filters import (
    SectorAuthorizationFilter,
    SectorFilter,
    SectorTagFilter,
)
from chats.apps.projects.models import Project
from chats.apps.projects.models.models import ProjectPermission
from chats.apps.projects.usecases.integrate_ticketers import IntegratedTicketers
from chats.apps.sectors.models import (
    Sector,
    SectorAuthorization,
    SectorHoliday,
    SectorTag,
)
from chats.apps.sectors.utils import get_country_from_timezone, get_country_holidays


class SectorViewset(viewsets.ModelViewSet):
    swagger_tag = "Sectors"
    queryset = Sector.objects.exclude(is_deleted=True)
    serializer_class = sector_serializers.SectorSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = SectorFilter
    lookup_field = "uuid"

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action == "list":
            permission_classes = [IsAuthenticated]
        elif self.action in ["create", "destroy"]:
            permission_classes = (IsAuthenticated, IsProjectAdmin)
        elif self.action == "agents":
            permission_classes = [HasAgentPermissionAnyQueueSector]
        else:
            permission_classes = [IsAuthenticated, IsSectorManager]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == "list":
            return sector_serializers.SectorReadOnlyListSerializer
        elif self.action == "retrieve":
            return sector_serializers.SectorReadOnlyRetrieveSerializer
        elif self.action in ["update", "partial_update"]:
            return sector_serializers.SectorUpdateSerializer

        return super().get_serializer_class()

    def perform_create(self, serializer):
        try:
            instance = serializer.save()
        except IntegrityError as e:
            raise exceptions.APIException(
                detail=f"Error when saving the sector. Exception: {str(e)}"
            )

        project = Project.objects.get(uuid=instance.project.uuid)

        content = {
            "project_uuid": str(instance.project.uuid),
            "name": instance.name,
            "config": {
                "project_auth": str(instance.external_token.pk),
                "sector_uuid": str(instance.uuid),
                "project_uuid": str(instance.project.uuid),
                "project_name_origin": instance.name,
            },
        }

        if settings.USE_WENI_FLOWS:
            flows_client = FlowRESTClient()
            response = flows_client.create_ticketer(**content)
            if response.status_code not in [
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ]:
                instance.delete()

                raise exceptions.APIException(
                    detail=(
                        f"[{response.status_code}] Error posting the sector/ticketer on flows. "
                        f"Exception: {response.content}"
                    )
                )

        if project.config and project.config.get("its_principal", False):
            integrate_use_case = IntegratedTicketers()
            integrate_use_case.integrate_individual_ticketer(
                project, instance.secondary_project
            )

    def update(self, request, *args, **kwargs):
        sector = self.get_object()
        config = request.data.get("config")
        if config and config.get("can_use_chat_completion"):
            openai_token = sector.project.set_chat_gpt_auth_token(
                request.META.get("HTTP_AUTHORIZATION")
            )
            if not openai_token:
                return Response(
                    {
                        "detail": "There is no chatgpt token configured on the integrations module"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        content = {
            "sector_uuid": str(instance.uuid),
            "user_email": self.request.query_params.get("user_email"),
        }

        if not settings.USE_WENI_FLOWS:
            return super().perform_destroy(instance)

        response = FlowRESTClient().destroy_sector(**content)
        if response.status_code not in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_204_NO_CONTENT,
        ]:
            raise exceptions.APIException(
                detail=f"[{response.status_code}] Error deleting the sector on flows. Exception: {response.content}"
            )
        instance.delete()
        return Response(
            {"is_deleted": True},
            status.HTTP_200_OK,
        )

    @action(detail=True, methods=["GET"])
    def agents(self, *args, **kwargs):
        instance = self.get_object()
        queue_agents = instance.queue_agents
        serializer = sector_serializers.SectorAgentsSerializer(queue_agents, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"])
    def count(self, request, *args, **kwargs):
        project_uuid = request.query_params.get("project")
        project = Project.objects.get(uuid=project_uuid)
        sector_count = project.get_sectors(user=request.user).count()
        if sector_count == 0:
            sector_count = (
                Sector.objects.filter(
                    project=project,
                    queues__authorizations__permission__user=request.user,
                    is_deleted=False,
                )
                .distinct()
                .count()
            )
        return Response({"sector_count": sector_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def authorization(self, request, *args, **kwargs):
        sector = self.get_object()
        user_email = request.data.get("user")
        if not user_email:
            return Response(
                {"Detail": "'user' field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permission = sector.get_permission(user_email)
        if not permission:
            return Response(
                {
                    "Detail": f"user {user_email} does not have an account or permission in this project"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sector_auth = sector.set_user_authorization(permission, 1)

        return Response(
            {
                "uuid": str(sector_auth.uuid),
                "user": sector_auth.permission.user.email,
                "sector": sector_auth.sector.name,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["GET", "POST"], url_path="worktime")
    def worktime(self, request, *args, **kwargs):
        sector = self.get_object()

        if request.method == "GET":
            working_hours = (sector.working_day or {}).get("working_hours", {})
            return Response({"working_hours": working_hours}, status=status.HTTP_200_OK)

        working_hours = request.data.get("working_hours", {})
        if not isinstance(working_hours, dict):
            return Response(
                {"detail": "Field 'working_hours' must be an object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        working_day = sector.working_day or {}
        working_day["working_hours"] = working_hours
        sector.working_day = working_day
        sector.save(update_fields=["working_day"])
        return Response({"working_hours": working_hours}, status=status.HTTP_200_OK)


class SectorTagPagination(LimitOffsetPagination):
    default_limit = 20


class SectorTagsViewset(viewsets.ModelViewSet):
    swagger_tag = "Sectors"
    queryset = SectorTag.objects.all().order_by("name")
    serializer_class = sector_serializers.SectorTagSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SectorTagFilter
    lookup_field = "uuid"
    pagination_class = SectorTagPagination

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.has_perm("accounts.can_communicate_internally"):
            queryset = queryset.all()

        else:
            queryset = queryset.filter(
                sector__project__in=ProjectPermission.objects.filter(
                    user=self.request.user
                ).values_list("project", flat=True)
            )

        if self.action != "list":
            self.filterset_class = None

        return queryset

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action == "list":
            permission_classes = [
                IsAuthenticated,
            ]
        else:
            permission_classes = (IsAuthenticated, IsSectorManager)

        return [permission() for permission in permission_classes]


class SectorAuthorizationViewset(viewsets.ModelViewSet):
    swagger_tag = "Sectors"
    queryset = SectorAuthorization.objects.all()
    serializer_class = sector_serializers.SectorAuthorizationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SectorAuthorizationFilter
    lookup_field = "uuid"

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["retrieve", "list"]:
            permission_classes = (IsAuthenticated, IsSectorManager)
        else:
            permission_classes = (IsAuthenticated, IsProjectAdmin)
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return sector_serializers.SectorAuthorizationReadOnlySerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"detail": "The user already have authorization on this sector"},
                status.HTTP_400_BAD_REQUEST,
            )

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.notify_user("create")

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.notify_user("update")

    def perform_destroy(self, instance):
        instance.notify_user("destroy")
        super().perform_destroy(instance)


class SectorHolidayViewSet(viewsets.ModelViewSet):
    swagger_tag = "Sectors"
    """
    ViewSet to manage holidays and special days by sectors.
    """

    serializer_class = sector_serializers.SectorHolidaySerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    lookup_field = "uuid"
    ordering = ["date"]

    def get_queryset(self):
        """
        Filter holidays based on user project permissions and sector parameter
        """
        queryset = SectorHoliday.objects.exclude(is_deleted=True).filter(
            sector__project__in=ProjectPermission.objects.filter(
                user=self.request.user
            ).values_list("project", flat=True)
        )

        sector_uuid = self.request.query_params.get("sector")
        if sector_uuid:
            queryset = queryset.filter(sector__uuid=sector_uuid)

        return queryset.order_by("date")

    def get_serializer_class(self):
        """
        Uses simplified serializer for listing
        """
        if self.action == "list":
            return sector_serializers.SectorHolidayListSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        """
        Permissions based on action
        """
        if self.action in ["list", "retrieve", "official_holidays"]:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated, IsSectorManager]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """
        Sector must be passed in the request body
        """
        serializer.save()

    def create(self, request, *args, **kwargs):
        """
        Suporta:
        - date: "YYYY-MM-DD" (one day)
        - date: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} (range in a single record)
        """
        body = request.data
        date_field = body.get("date")

        if isinstance(date_field, dict):
            start_str = date_field.get("start")
            end_str = date_field.get("end")

            if not isinstance(start_str, str) or not start_str:
                return Response(
                    {"detail": "date.start is required (YYYY-MM-DD)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not isinstance(end_str, str) or not end_str:
                end_str = start_str

            start_str = start_str.strip()
            end_str = end_str.strip()

            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {
                        "detail": "Date has wrong format. Use YYYY-MM-DD or {'start','end'} with this format."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if end_date < start_date:
                return Response(
                    {"detail": "date.end must be greater than or equal to date.start"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payload = {
                "sector": body.get("sector"),
                "date": start_date,
                "date_end": end_date,
                "day_type": body.get("day_type", SectorHoliday.CLOSED),
                "start_time": body.get("start_time"),
                "end_time": body.get("end_time"),
                "description": body.get("description", ""),
                "its_custom": bool(body.get("its_custom", False)),
                "repeat": bool(body.get("repeat", False)),
            }

            serializer = self.get_serializer(data=payload)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get", "patch"])
    def official_holidays(self, request):
        """
        GET /api/v1/sector_holiday/official_holidays/?project=<uuid>&year=2025
        PATCH /api/v1/sector_holiday/official_holidays/?sector=<uuid>

        GET: retorna feriados oficiais inferidos pelo timezone do projeto.
        PATCH: habilita/desabilita feriados oficiais por data (YYYY-MM-DD) para o setor.
        """
        if request.method.upper() == "PATCH":
            sector_uuid = request.query_params.get("sector")
            if not sector_uuid:
                return Response(
                    {"detail": "Parameter 'sector' is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            enabled_dates = request.data.get("enabled_holidays", [])
            disabled_dates = request.data.get("disabled_holidays", [])

            if not isinstance(enabled_dates, list) or not isinstance(
                disabled_dates, list
            ):
                return Response(
                    {"detail": "enabled_holidays and disabled_holidays must be lists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                sector = Sector.objects.get(uuid=sector_uuid)
            except Sector.DoesNotExist:
                return Response(
                    {"detail": "Sector not found"}, status=status.HTTP_404_NOT_FOUND
                )

            def parse_date_str(ds):
                if not isinstance(ds, str) or not ds:
                    return None
                try:
                    return datetime.strptime(ds.strip(), "%Y-%m-%d").date()
                except ValueError:
                    return None

            dates_to_touch = [
                *(parse_date_str(d) for d in enabled_dates),
                *(parse_date_str(d) for d in disabled_dates),
            ]
            years = {d.year for d in dates_to_touch if d}
            official_by_year = {}
            country_code = get_country_from_timezone(str(sector.project.timezone))
            for y in years:
                official_by_year[y] = get_country_holidays(country_code, y) or {}

            enabled_count = 0
            disabled_count = 0
            errors = []

            for ds in enabled_dates:
                d = parse_date_str(ds)
                if not d:
                    errors.append(f"Invalid date format: {ds}")
                    continue

                obj = SectorHoliday.objects.filter(sector=sector, date=d).first()
                name = official_by_year.get(d.year, {}).get(d, "")

                if obj:
                    updates = {}
                    if obj.is_deleted:
                        obj.is_deleted = False
                        updates["is_deleted"] = False
                    if obj.day_type != SectorHoliday.CLOSED:
                        obj.day_type = SectorHoliday.CLOSED
                        updates["day_type"] = SectorHoliday.CLOSED
                    if obj.its_custom:
                        obj.its_custom = False
                        updates["its_custom"] = False
                    if name and obj.description != name:
                        obj.description = name
                        updates["description"] = name
                    if updates:
                        obj.save()
                    enabled_count += 1
                else:
                    SectorHoliday.objects.create(
                        sector=sector,
                        date=d,
                        day_type=SectorHoliday.CLOSED,
                        description=name,
                        its_custom=False,
                    )
                    enabled_count += 1

            for ds in disabled_dates:
                d = parse_date_str(ds)
                if not d:
                    errors.append(f"Invalid date format: {ds}")
                    continue
                obj = SectorHoliday.objects.filter(sector=sector, date=d).first()
                if obj and not obj.is_deleted:
                    obj.is_deleted = True
                    obj.save(update_fields=["is_deleted"])
                    disabled_count += 1

            return Response(
                {
                    "enabled": enabled_count,
                    "disabled": disabled_count,
                    "errors": errors,
                },
                status=status.HTTP_200_OK,
            )

        project_uuid = request.query_params.get("project")
        year_param = request.query_params.get("year")

        if not project_uuid:
            return Response(
                {"detail": "Parameter 'project' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            return Response(
                {"detail": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )

        has_access = ProjectPermission.objects.filter(
            user=request.user, project=project
        ).exists()
        if not has_access:
            return Response(
                {"detail": "You dont have permission in this project."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not year_param:
            year = timezone.now().astimezone(project.timezone).year
        else:
            try:
                year = int(year_param)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Invalid 'year'. Use an integer like 2025."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        country_code = get_country_from_timezone(str(project.timezone))
        official_holidays = get_country_holidays(country_code, year)

        holidays_list = [
            {
                "date": holiday_date.strftime("%Y-%m-%d"),
                "name": holiday_name,
                "country_code": country_code,
            }
            for holiday_date, holiday_name in official_holidays.items()
        ]

        return Response(
            {
                "country_code": country_code,
                "year": year,
                "holidays": sorted(holidays_list, key=lambda x: x["date"]),
            }
        )

    @action(detail=False, methods=["post"])
    def import_official_holidays(self, request):
        """
        POST /api/v1/sector_holiday/import_official_holidays/
        Create holidays in bulk from selected official holidays

        Body:
        {
            "sector": "uuid",
            "year": 2024,
            "holidays": ["2024-12-25", "2024-01-01"]  # Selected dates
        }
        """
        sector_uuid = request.data.get("sector")
        year = request.data.get("year", timezone.now().year)
        selected_holidays = request.data.get("enabled_holidays", [])

        if not sector_uuid:
            return Response(
                {"detail": "Field 'sector' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sector = Sector.objects.get(uuid=sector_uuid)
            country_code = get_country_from_timezone(str(sector.project.timezone))
            official_holidays = get_country_holidays(country_code, int(year))

            created_holidays = []
            errors = []

            for holiday_date_str in selected_holidays:
                try:
                    holiday_date = datetime.strptime(
                        holiday_date_str, "%Y-%m-%d"
                    ).date()

                    if holiday_date not in official_holidays:
                        errors.append(
                            f"Date {holiday_date_str} is not an official holiday"
                        )
                        continue

                    if SectorHoliday.objects.filter(
                        sector=sector, date=holiday_date, is_deleted=False
                    ).exists():
                        errors.append(f"Holiday for {holiday_date_str} already exists")
                        continue

                    holiday = SectorHoliday.objects.create(
                        sector=sector,
                        date=holiday_date,
                        day_type=SectorHoliday.CLOSED,
                        description=official_holidays[holiday_date],
                    )

                    created_holidays.append(
                        {
                            "uuid": str(holiday.uuid),
                            "date": holiday_date_str,
                            "description": holiday.description,
                        }
                    )

                except ValueError:
                    errors.append(f"Invalid date format: {holiday_date_str}")
                except Exception as e:
                    errors.append(
                        f"Error creating holiday for {holiday_date_str}: {str(e)}"
                    )

            return Response(
                {
                    "created": len(created_holidays),
                    "holidays": created_holidays,
                    "errors": errors,
                },
                status=(
                    status.HTTP_201_CREATED
                    if created_holidays
                    else status.HTTP_400_BAD_REQUEST
                ),
            )

        except Sector.DoesNotExist:
            return Response(
                {"detail": "Sector not found"}, status=status.HTTP_404_NOT_FOUND
            )
