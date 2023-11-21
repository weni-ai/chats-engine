from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from ..filters import DiscussionFilter
from ..models import Discussion
from ..serializers import (
    DiscussionCreateSerializer,
    DiscussionDetailSerializer,
    DiscussionListSerializer,
)
from ._discussion_message_actions import DiscussionMessageActionsMixin
from ._discussion_user_actions import DiscussionUserActionsMixin
from .permissions import CanManageDiscussion

User = get_user_model()


class DiscussionViewSet(
    viewsets.ModelViewSet, DiscussionUserActionsMixin, DiscussionMessageActionsMixin
):
    queryset = Discussion.objects.all()
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = DiscussionFilter
    permission_classes = [IsAuthenticated, CanManageDiscussion]
    lookup_field = "uuid"

    def filter_queryset(self, queryset):
        if self.action == "list":
            return super().filter_queryset(queryset)
        return queryset

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
