from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.groups_sectors.filters import GroupSectorFilter
from chats.apps.api.v1.groups_sectors.serializers import (
    GroupSectorAuthorizationSerializer,
    GroupSectorListSerializer,
    GroupSectorSerializer,
    GroupSectorUpdateSerializer,
)
from chats.apps.api.v1.permissions import IsProjectAdmin
from chats.apps.queues.models import QueueAuthorization
from chats.apps.sectors.models import GroupSector, GroupSectorAuthorization, Sector
from chats.apps.sectors.usecases import (
    AddSectorToGroupSectorUseCase,
    GroupSectorAuthorizationCreationUseCase,
    GroupSectorAuthorizationDeletionUseCase,
    RemoveSectorFromGroupSectorUseCase,
    UpdateAgentQueueAuthorizationsUseCase,
)


class GroupSectorViewset(viewsets.ModelViewSet):
    queryset = GroupSector.objects.exclude(is_deleted=True)
    serializer_class = GroupSectorSerializer
    filterset_class = GroupSectorFilter
    permission_classes = [IsAuthenticated, IsProjectAdmin]
    lookup_field = "uuid"

    def get_serializer_class(self):
        if self.action == "list":
            return GroupSectorListSerializer
        elif self.action == "update":
            return GroupSectorUpdateSerializer
        return GroupSectorSerializer

    def get_queryset(self):
        if self.action != "list":
            self.filterset_class = None
        return super().get_queryset()

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        for sector in instance.sectors.all():
            RemoveSectorFromGroupSectorUseCase(
                sector_uuid=sector.uuid, group_sector=instance
            ).execute()
        instance.delete()

    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[IsAuthenticated, IsProjectAdmin],
        url_path="queue",
    )
    def list_queues(self, request, *args, **kwargs):
        """
        GET /v1/group_sector/queue/?sectors=uuid1,uuid2
        """
        sectors_param = request.query_params.get("sectors", "")
        sector_uuids = [s.strip() for s in sectors_param.split(",") if s.strip()]
        if not sector_uuids:
            return Response(
                {"message": "sectors is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        selected_sectors = (
            Sector.objects.filter(uuid__in=sector_uuids, is_deleted=False)
            .select_related("project")
            .prefetch_related("queues")
        )

        response_payload = {}
        for sector in selected_sectors:
            sector_queues = sector.queues.filter(is_deleted=False).only("uuid", "name")
            response_payload[str(sector.uuid)] = {
                "sector_name": sector.name,
                "queues": [
                    {"queue_name": q.name, "uuid": str(q.uuid)} for q in sector_queues
                ],
            }
        return Response(response_payload, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[IsAuthenticated, IsProjectAdmin],
        url_path="permissions",
    )
    def list_permissions(self, request, *args, **kwargs):
        """
        GET /v1/group_sector/permissions/?sectors=uuid1,uuid2
        Response:
        {
          "[agent_email]": {
            "[sectorUuid]": { "sector_name": "string", "permissions": ["queueUuid", ...] }
          }
        }
        """
        sectors_param = request.query_params.get("sectors", "")
        sector_uuids = [s.strip() for s in sectors_param.split(",") if s.strip()]
        if not sector_uuids:
            return Response(
                {"message": "sectors is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        selected_sectors = Sector.objects.filter(
            uuid__in=sector_uuids, is_deleted=False
        )
        queue_authorizations = (
            QueueAuthorization.objects.filter(
                queue__sector__in=selected_sectors, queue__is_deleted=False
            )
            .select_related("permission__user", "queue__sector")
            .only(
                "queue__uuid",
                "queue__sector__uuid",
                "queue__sector__name",
                "permission__user__email",
            )
        )

        response_payload = {}
        for authorization in queue_authorizations:
            agent_email = authorization.permission.user.email
            sector_uuid = str(authorization.queue.sector.uuid)
            sector_name = authorization.queue.sector.name
            agent_entry = response_payload.setdefault(agent_email, {})
            sector_permissions_entry = agent_entry.setdefault(
                sector_uuid, {"sector_name": sector_name, "permissions": []}
            )
            sector_permissions_entry["permissions"].append(
                str(authorization.queue.uuid)
            )

        return Response(response_payload, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[IsAuthenticated, IsProjectAdmin],
    )
    def add_sector(self, request, *args, **kwargs):
        sector_group = self.get_object()
        sector_uuid = request.data.get("sector", None)
        if sector_uuid is None:
            response = {
                "message": "Sector not informed",
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            AddSectorToGroupSectorUseCase(
                sector_uuid=sector_uuid, group_sector=sector_group
            ).execute()
            response = {
                "message": "Sector added to sector group",
                "sector_group": sector_group.uuid,
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            response = {
                "message": str(e),
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[IsAuthenticated, IsProjectAdmin],
    )
    def remove_sector(self, request, *args, **kwargs):
        sector_group = self.get_object()
        sector = request.data.get("sector", None)
        if sector is None:
            response = {
                "message": "Sector not informed",
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            RemoveSectorFromGroupSectorUseCase(
                sector_uuid=sector, group_sector=sector_group
            ).execute()
            response = {
                "message": f"Sector {sector} removed from sector group {sector_group.uuid}",
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            response = {
                "message": str(e),
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GroupSectorAuthorizationViewset(viewsets.ModelViewSet):
    queryset = GroupSectorAuthorization.objects.all()
    serializer_class = GroupSectorAuthorizationSerializer
    permission_classes = [IsAuthenticated, IsProjectAdmin]
    filterset_fields = ["group_sector", "role"]
    lookup_field = "uuid"

    def create(self, request, *args, **kwargs):
        group_sector_uuid = request.data.get("group_sector", None)
        permission_uuid = request.data.get("permission", None)
        role = request.data.get("role", None)
        enabled_queues = request.data.get("enabled_queues", None)
        disabled_queues = request.data.get("disabled_queues", None)

        if group_sector_uuid is None or permission_uuid is None or role is None:
            return Response(
                {"message": "group_sector, permission and role are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Retrocompatibilidade: sem listas → lógica antiga
        if not enabled_queues and not disabled_queues:
            try:
                GroupSectorAuthorizationCreationUseCase(
                    group_sector_uuid=group_sector_uuid,
                    permission_uuid=permission_uuid,
                    role=role,
                ).execute()
                return Response(
                    {
                        "message": "Group sector authorization created successfully",
                        "group_sector": group_sector_uuid,
                        "permission": permission_uuid,
                        "role": role,
                    },
                    status=status.HTTP_201_CREATED,
                )
            except Exception as e:
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Nova lógica: listas só fazem sentido para ROLE_AGENT
        try:
            role = int(role)
        except Exception:
            return Response(
                {"message": "invalid role"}, status=status.HTTP_400_BAD_REQUEST
            )
        if role != GroupSectorAuthorization.ROLE_AGENT:
            return Response(
                {
                    "message": "enabled_queues/disabled_queues supported only for agent role"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            GroupSectorAuthorization.objects.get_or_create(
                group_sector_id=group_sector_uuid,
                permission_id=permission_uuid,
                role=GroupSectorAuthorization.ROLE_AGENT,
            )
            UpdateAgentQueueAuthorizationsUseCase(
                group_sector_uuid=group_sector_uuid,
                permission_uuid=permission_uuid,
                enabled_queue_uuids=enabled_queues or [],
                disabled_queue_uuids=disabled_queues or [],
            ).execute()
            return Response(
                {
                    "message": "Agent queue authorizations updated successfully",
                    "group_sector": group_sector_uuid,
                    "permission": permission_uuid,
                    "role": role,
                    "enabled_queues": enabled_queues or [],
                    "disabled_queues": disabled_queues or [],
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            GroupSectorAuthorizationDeletionUseCase(instance).execute()
            response = {
                "message": "Group sector authorization deleted successfully",
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            response = {
                "message": str(e),
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
