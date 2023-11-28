from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..exceptions import DiscussionValidationException
from ..filters import DiscussionFilter
from ..models import Discussion
from ..serializers import (
    DiscussionCreateSerializer,
    DiscussionDetailSerializer,
    DiscussionListSerializer,
)
from ..usecases import CreateDiscussionUseCase
from ._discussion_message_actions import DiscussionMessageActionsMixin
from ._discussion_user_actions import DiscussionUserActionsMixin
from .permissions import CanManageDiscussion

User = get_user_model()


class DiscussionViewSet(
    viewsets.ModelViewSet, DiscussionMessageActionsMixin, DiscussionUserActionsMixin
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

    def create(self, request, *args, **kwargs):
        try:
            creation_data = self.get_serializer(data=request.data)
            creation_data.is_valid(raise_exception=True)
            discussion = self.perform_create(creation_data)
            serialized_result = self.get_serializer(discussion)
            headers = self.get_success_headers(serialized_result.data)

            return Response(
                serialized_result.data, status=status.HTTP_201_CREATED, headers=headers
            )
        except DiscussionValidationException as err:
            return Response(
                {"Detail": f"{err}"},
                status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {"detail": "The room already have an open discussion."},
                status.HTTP_409_CONFLICT,
            )
        except Exception as err:
            return Response(
                {"Detail": f"{err}"},
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def perform_create(self, serializer):
        return CreateDiscussionUseCase(
            serialized_data=serializer.validated_data, created_by=self.request.user
        ).execute()
