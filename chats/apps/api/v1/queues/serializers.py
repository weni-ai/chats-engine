from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserSerializer
from chats.apps.queues.models import Queue, QueueAuthorization


class QueueSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source="sector.name", read_only=True)

    class Meta:
        model = Queue
        fields = "__all__"

    def validate(self, data):
        """
        Check if queue already exist in sector.
        """
        name = data.get("name")
        if name:
            if name == "":
                raise serializers.ValidationError(
                    {"detail": _("The name field can't be blank.")}
                )
            if self.instance:
                if Queue.objects.filter(
                    sector=self.instance.sector, name=name
                ).exists():
                    raise serializers.ValidationError(
                        {"detail": _("This queue already exists.")}
                    )
            else:
                if Queue.objects.filter(sector=data["sector"], name=name).exists():
                    raise serializers.ValidationError(
                        {"detail": _("This queue already exists.")}
                    )
        return data


class QueueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class QueueReadOnlyListSerializer(serializers.ModelSerializer):
    agents = serializers.SerializerMethodField()
    sector_name = serializers.CharField(source="sector.name", read_only=True)

    class Meta:
        model = Queue
        fields = ["uuid", "name", "agents", "created_on", "sector_name"]

    def get_agents(self, queue: Queue):
        return queue.agent_count


class QueueAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueAuthorization
        fields = "__all__"

    def validate(self, data):
        """
        Check if user already exist in queue.
        """
        queue_user = QueueAuthorization.objects.filter(
            permission=data["permission"], queue=data["queue"]
        )
        if queue_user:
            raise serializers.ValidationError(
                {"detail": _("you cant add a user two times in same queue.")}
            )
        return data


class QueueAuthorizationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueAuthorization
        fields = "__all__"

        extra_kwargs = {field: {"required": False} for field in fields}


class QueueAuthorizationReadOnlyListSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = QueueAuthorization
        fields = [
            "uuid",
            "queue",
            "role",
            "user",
        ]

    def get_user(self, auth):
        return UserSerializer(auth.permission.user).data


class QueueSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = ["uuid", "name"]
