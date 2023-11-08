from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..filters import DiscussionFilter
from ..models import Discussion, DiscussionUser
from ..serializers import (
    DiscussionCreateSerializer,
    DiscussionDetailSerializer,
    DiscussionListSerializer,
    DiscussionUserListSerializer,
)
from .permissions import CanManageDiscussion

User = get_user_model()


class DiscussionUserActionsMixin:
    """This should be used with a Discussion model viewset"""

    @action(detail=True, methods=["POST"], url_name="add_agents", filterset_class=None)
    def add_agents(self, request, *args, **kwargs):
        try:
            user = request.data.get("user_email")
            user = User.objects.get(email=user)
            discussion = self.get_object()
            added_agent = discussion.create_discussion_user(
                from_user=request.user, to_user=user
            )
            return Response(
                {
                    "first_name": added_agent.user.first_name,
                    "last_name": added_agent.user.last_name,
                    "role": added_agent.role,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as error:
            return Response(
                {"detail": f"{type(error)}: {error}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["GET"], url_name="list_agents", filterset_class=None)
    def list_agents(self, request, *args, **kwargs):
        discussion = self.get_object()

        queryset = DiscussionUser.objects.filter(discussion=discussion)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = DiscussionUserListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = DiscussionUserListSerializer(queryset, many=True)
        return Response(serializer.data)


class DiscussionViewSet(viewsets.ModelViewSet, DiscussionUserActionsMixin):
    queryset = Discussion.objects.all()
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = DiscussionFilter
    permission_classes = [IsAuthenticated, CanManageDiscussion]
    lookup_field = "uuid"

    def get_paginated_response(self, data):
        return super().get_paginated_response(data)

    def filter_queryset(self, queryset):
        if self.action in ["destroy", "retrieve"]:
            return queryset
        return super().filter_queryset(queryset)

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
