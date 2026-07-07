import logging

from django.conf import settings
from django.db.models import (
    BooleanField,
    Case,
    F,
    IntegerField,
    Value,
    When,
    fields,
)
from django.db.models import Q, CharField
from django.db.models.functions import Extract, Now, Concat
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.mixins import ListModelMixin
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet
from rest_framework.filters import SearchFilter, OrderingFilter
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

from chats.apps.api.authentication.classes import JWTAuthentication
from chats.apps.api.authentication.permissions import (
    HasInternalAuthenticationPermission,
)
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.api.v1.internal.rooms.serializers import (
    RoomInternalListSerializer,
    InternalProtocolRoomsSerializer,
)
from chats.apps.dashboard.models import MetricGoal
from chats.apps.rooms.models import Room
from chats.apps.api.pagination import CustomCursorPagination

from chats.apps.api.v1.internal.rooms.filters import (
    RoomFilter,
    InternalProtocolRoomsFilter,
)
from datetime import timedelta


logger = logging.getLogger(__name__)


class InternalListRoomsViewSet(viewsets.ReadOnlyModelViewSet):
    swagger_tag = "Rooms"
    queryset = Room.objects.all()
    serializer_class = RoomInternalListSerializer
    lookup_field = "uuid"
    authentication_classes = [
        JWTAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES

    def get_permissions(self):
        if getattr(self.request, "jwt_payload", None):
            return [HasInternalAuthenticationPermission()]
        return [permissions.IsAuthenticated(), ModuleHasPermission()]

    filter_backends = [
        filters.OrderingFilter,
        filters.SearchFilter,
        DjangoFilterBackend,
    ]
    ordering = ["-created_on"]
    ordering_fields = [
        "created_on",
        "ended_at",
        "is_active",
        "urn",
        "uuid",
        "user_full_name",
        "user__email",
        "user__first_name",
        "user__last_name",
        "contact__name",
        "queue__name",
        "queue__sector__name",
        "first_user_assigned_at",
        "user_assigned_at",
        "added_to_queue_at",
        "queue_time",
        "waiting_time",
        "duration",
        "first_response_time",
        "protocol",
    ]
    search_fields = [
        "contact__external_id",
        "contact__name",
        "user__email",
        "urn",
    ]
    filterset_class = RoomFilter

    pagination_class = LimitOffsetPagination
    pagination_class.page_size = 5

    def _is_pending_response_feature_active(self) -> bool:
        """
        Whether to compute and return the `pending_response` field on each room.

        Gated by a feature flag so the extra LEFT JOIN on `msgs_message` can be
        disabled per project if it starts hurting database performance.
        """
        if hasattr(self, "_pending_response_feature_active_cached"):
            return self._pending_response_feature_active_cached

        active = False
        project_uuid = (
            self.request.query_params.get("project") if self.request else None
        )
        try:
            attributes = {"projectUUID": str(project_uuid)} if project_uuid else {}
            active = is_feature_active_for_attributes(
                key=settings.INTERNAL_ROOMS_LIST_PENDING_RESPONSE_FEATURE_FLAG_KEY,
                attributes=attributes,
            )
        except Exception as e:
            logger.error("Error checking pending_response feature flag: %s", e)

        self._pending_response_feature_active_cached = active
        return active

    def _get_active_goals_by_metric(self) -> dict:
        """Return the active ``MetricGoal`` rows for the requested project, keyed by metric.

        Fetched once per request (not per room) to avoid N+1 queries when
        computing the ``goals_metrics`` field on each serialized room.
        """
        if hasattr(self, "_active_goals_by_metric_cached"):
            return self._active_goals_by_metric_cached

        project_uuid = self.request.query_params.get("project") if self.request else None
        goals_by_metric: dict = {}
        if project_uuid:
            goals = MetricGoal.objects.filter(
                project__uuid=project_uuid, is_active=True
            )
            goals_by_metric = {goal.metric: goal for goal in goals}

        self._active_goals_by_metric_cached = goals_by_metric
        return goals_by_metric

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["include_pending_response"] = self._is_pending_response_feature_active()
        context["active_goals_by_metric"] = self._get_active_goals_by_metric()
        return context

    def get_queryset(self):
        queryset = super().get_queryset()

        annotations = {
            "user_full_name": Concat(
                F("user__first_name"),
                Value(" "),
                F("user__last_name"),
                output_field=CharField(),
            ),
            "queue_time": Case(
                When(
                    added_to_queue_at__isnull=False,
                    then=Now() - F("added_to_queue_at"),
                ),
                default=Value(timedelta(0)),
                output_field=fields.DurationField(),
            ),
            "waiting_time": Case(
                When(
                    added_to_queue_at__isnull=False,
                    user_assigned_at__isnull=False,
                    then=F("user_assigned_at") - F("added_to_queue_at"),
                ),
                default=Value(timedelta(0)),
                output_field=fields.DurationField(),
            ),
            "duration": Case(
                When(
                    is_active=True,
                    user__isnull=False,
                    first_user_assigned_at__isnull=False,
                    then=Now() - F("first_user_assigned_at"),
                ),
                When(
                    is_active=False,
                    ended_at__isnull=False,
                    first_user_assigned_at__isnull=False,
                    then=F("ended_at") - F("first_user_assigned_at"),
                ),
                default=Value(timedelta(0)),
                output_field=fields.DurationField(),
            ),
            "first_response_time": Case(
                When(
                    metric__first_response_time__gt=0,
                    then=F("metric__first_response_time"),
                ),
                When(
                    is_active=True,
                    user__isnull=False,
                    first_user_assigned_at__isnull=False,
                    then=Extract(Now() - F("first_user_assigned_at"), "epoch"),
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
        }

        if self._is_pending_response_feature_active():
            annotations["pending_response"] = Case(
                When(
                    last_message_contact__isnull=False,
                    unread_messages_count=0,
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )

        queryset = queryset.annotate(**annotations)

        return queryset


class InternalProtocolRoomsViewSet(ListModelMixin, GenericViewSet):
    queryset = Room.objects.all()
    serializer_class = InternalProtocolRoomsSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = InternalProtocolRoomsFilter
    authentication_classes = [
        JWTAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    search_fields = ["protocol"]
    ordering = ["protocol"]
    ordering_fields = ["protocol"]
    pagination_class = CustomCursorPagination

    def get_permissions(self):
        if getattr(self.request, "jwt_payload", None):
            return [HasInternalAuthenticationPermission()]
        return [permissions.IsAuthenticated(), ModuleHasPermission()]

    def get_queryset(self):
        return super().get_queryset().exclude(Q(protocol__isnull=True) | Q(protocol=""))
