from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from chats.apps.projects.models import ProjectPermission

from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import SectorAuthorization


class QueueFilter(filters.FilterSet):
    class Meta:
        model = Queue
        fields = ["sector"]

    sector = filters.CharFilter(
        field_name="sector",
        required=True,
        method="filter_sector",
        help_text=_("sector's ID"),
    )

    def filter_sector(self, queryset, name, value):
        """
        Return queue given a user, will check if the user is the project admin or
        if they have manager role on sectors inside the project, or if he as a agent.
        """
        try:
            if ProjectPermission.objects.filter(user=self.request.user):
                queues = Queue.objects.all()
            elif SectorAuthorization.objects.filter(
                user=self.request.user, sector__uuid=value
            ):
                queues = Queue.objects.filter(sector__uuid=value)
            elif QueueAuthorization.objects.filter(
                user=self.request.user, queue__sector__uuid=value
            ):
                agent_auth = QueueAuthorization.objects.filter(
                    user=self.request.user, queue__sector__uuid=value
                )
                queues = Queue.objects.filter(authorizations__in=agent_auth)
            else:
                queues = Queue.objects.none()
        except (
            ProjectPermission.DoesNotExist,
            SectorAuthorization.DoesNotExist,
            QueueAuthorization.DoesNotExist,
        ):
            return Queue.objects.none()
        return queues


class QueueAuthorizationFilter(filters.FilterSet):
    class Meta:
        model = QueueAuthorization
        fields = ["queue"]

    queue = filters.CharFilter(
        field_name="queue",
        required=True,
        method="filter_queue",
        help_text=_("queue's ID"),
    )

    status = filters.CharFilter(
        field_name="status",
        required=False,
        method="filter_status",
        help_text=_("User Status"),
    )

    def filter_status(self, queryset, name, value):
        return queryset.filter(permission__status=value)

    def filter_queue(self, queryset, name, value):
        return queryset.filter(queue=value)
