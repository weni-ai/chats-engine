from django_filters import rest_framework as filters

from chats.apps.queues.models import Queue


class QueueFlowFilter(filters.FilterSet):
    class Meta:
        model = Queue
        fields = ["sector", "name"]
