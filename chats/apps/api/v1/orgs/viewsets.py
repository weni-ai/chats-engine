from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from chats.apps.projects.models import Project
from .serializers import OrgProjectSerializer


class OrgProjectViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = OrgProjectSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "org"
    lookup_url_kwarg = "org"

    def get_queryset(self):
        its_principal = self.request.query_params.get("its_principal")
        queryset = Project.objects.filter(org=self.kwargs["org"])

        if its_principal is not None:
            its_principal = its_principal.lower() == "true"
            queryset = queryset.filter(
                Q(config__its_principal=its_principal)
                | Q(
                    config__has_key="its_principal", config__its_principal=its_principal
                )
            )

        return queryset
