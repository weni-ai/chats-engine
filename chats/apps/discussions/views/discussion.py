from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, pagination, parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..filters import DiscussionFilter
from ..models import Discussion
from ..serializers import DiscussionCreateSerializer


class DiscussionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Discussion.objects.all()
    serializer_class = DiscussionCreateSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = DiscussionFilter
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
