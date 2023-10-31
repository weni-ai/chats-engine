from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from ..filters import DiscussionFilter
from ..models import Discussion
from ..serializers import (
    DiscussionCreateSerializer,
    DiscussionDetailSerializer,
    DiscussionListSerializer,
    DiscussionUserListSerializer,
)


class DiscussionUserActionsMixin:
    @action(
        detail=True,
        methods=["POST"],
        url_name="add_agents",
        serializer_class=DiscussionUserListSerializer,
    )
    def add_agents(self):
        pass


class DiscussionViewSet(viewsets.ModelViewSet, DiscussionUserActionsMixin):
    queryset = Discussion.objects.all()
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = DiscussionFilter
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == "create":
            return DiscussionCreateSerializer
        elif self.action == "list":
            return DiscussionListSerializer
        elif self.action == "retrieve":
            return DiscussionDetailSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "create":
            context["user"] = self.request.user
        return context
