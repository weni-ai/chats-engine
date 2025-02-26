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
from chats.apps.sectors.models import GroupSector, GroupSectorAuthorization
from chats.apps.sectors.usecases import (
    AddSectorToGroupSectorUseCase,
    GroupSectorAuthorizationCreationUseCase,
    GroupSectorAuthorizationDeletionUseCase,
    RemoveSectorFromGroupSectorUseCase,
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

    def perform_create(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        for sector in instance.sectors.all():
            RemoveSectorFromGroupSectorUseCase(
                sector_uuid=sector.uuid, group_sector=instance
            ).execute()
        instance.delete()

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
        if group_sector_uuid is None or permission_uuid is None or role is None:
            response = {
                "message": "group_sector, permission and role are required",
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        try:
            GroupSectorAuthorizationCreationUseCase(
                group_sector_uuid=group_sector_uuid,
                permission_uuid=permission_uuid,
                role=role,
            ).execute()
            response = {
                "message": "Group sector authorization created successfully",
                "group_sector": group_sector_uuid,
                "permission": permission_uuid,
                "role": role,
            }
            return Response(response, status=status.HTTP_201_CREATED)
        except Exception as e:
            response = {
                "message": str(e),
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

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
