from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.api.v1.permissions import IsProjectAdmin
from chats.apps.sectors.models import GroupSector, GroupSectorAuthorization
from chats.apps.api.v1.groups_sectors.serializers import (
    GroupSectorSerializer,
    GroupSectorListSerializer,
    GroupSectorUpdateSerializer,
    GroupSectorAuthorizationSerializer,
)
from chats.apps.api.v1.groups_sectors.filters import GroupSectorFilter


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

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[IsAuthenticated, IsProjectAdmin],
    )
    def add_sector(self, request, *args, **kwargs):
        sector_group = self.get_object()
        sector = request.data.get("sector", None)
        if sector is None:
            response = {
                "message": "Sector not informed",
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            sector_group.add_sector(sector)
            sector_group.save()
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
            sector_group.remove_sector(sector)
            sector_group.save()
            response = {
                "message": "Sector removed from sector group",
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
    def add_authorization(self, request, *args, **kwargs):
        group_sector = self.get_object()
        serializer = GroupSectorAuthorizationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            authorization = GroupSectorAuthorization.objects.create(
                group_sector=group_sector,
                permission=serializer.validated_data["permission"],
                role=serializer.validated_data["role"]
            )
            response = {
                "message": "Authorization added successfully",
                "authorization": GroupSectorAuthorizationSerializer(authorization).data
            }
            return Response(response, status=status.HTTP_201_CREATED)
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
    def remove_authorization(self, request, *args, **kwargs):
        group_sector = self.get_object()
        permission = request.data.get("permission", None)

        if permission is None:
            response = {
                "message": "Permission not informed",
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            authorization = GroupSectorAuthorization.objects.get(
                group_sector=group_sector,
                permission_id=permission
            )
            authorization.delete()
            response = {
                "message": "Authorization removed successfully",
            }
            return Response(response, status=status.HTTP_200_OK)
        except GroupSectorAuthorization.DoesNotExist:
            response = {
                "message": "Authorization not found",
            }
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            response = {
                "message": str(e),
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
