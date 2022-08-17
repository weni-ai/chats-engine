from rest_framework import serializers
from chats.apps.queues.models import Queue, QueueAuthorization
from django.utils.translation import gettext_lazy as _

# Sector Queue serializers


class SectorQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = "__all__"

    def validate(self, data):
        """
        Check if queue already exist in sector.
        """
        if self.instance:
            if Queue.objects.filter(sector=self.instance.sector, name=data['name']).exists():
                raise serializers.ValidationError({
                'queue': _("This queue already exists.")
                })
        else:
            if Queue.objects.filter(sector=data['sector'], name=data['name']).exists():
                raise serializers.ValidationError({
                'queue': _("This queue already exists.")
                })       
        return data


class SectorQueueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class SectorQueueReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()

    class Meta:
        model = Queue
        fields = ["uuid", "name", "agents"]

    def get_agents(self, sectorqueue: Queue):
        return sectorqueue.agent_count


class SectorQueueAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueAuthorization
        fields = "__all__"

    def validate(self, data):
        """
        Check if user already exist in queue.
        """
        queue_user = QueueAuthorization.objects.filter(user=data['user'], queue=data['queue'])
        if queue_user:
            raise serializers.ValidationError({
               'user': _("you cant add a user two times in same queue.")
            })
        return data


class QueueAuthorizationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueAuthorization
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class QueueAuthorizationReadOnlyListSerializer(serializers.ModelSerializer):

    class Meta:
        model = QueueAuthorization
        fields = ["id", "uuid", "queue", "role", "user"]