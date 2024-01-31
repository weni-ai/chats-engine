from rest_framework import serializers

from chats.apps.rooms.models import Room


class DashboardAgentsSerializer(serializers.Serializer):
    first_name = serializers.CharField(allow_null=True, required=False)
    email = serializers.EmailField(allow_null=True, required=False)
    agent_status = serializers.CharField(allow_null=True, required=False)
    closed_rooms = serializers.IntegerField(allow_null=True, required=False)
    opened_rooms = serializers.IntegerField(allow_null=True, required=False)


class DashboardRawDataSerializer(serializers.Serializer):
    active_rooms = serializers.IntegerField(allow_null=True, required=False)
    closed_rooms = serializers.IntegerField(allow_null=True, required=False)
    transfer_count = serializers.IntegerField(allow_null=True, required=False)
    queue_rooms = serializers.IntegerField(allow_null=True, required=False)


class DashboardSectorSerializer(serializers.Serializer):
    name = serializers.CharField(allow_null=True, required=False)
    waiting_time = serializers.IntegerField(allow_null=True, required=False)
    response_time = serializers.IntegerField(allow_null=True, required=False)
    interact_time = serializers.IntegerField(allow_null=True, required=False)


class DashboardClosedRoomSerializer(serializers.ModelSerializer):
    closed_rooms = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["closed_rooms"]


class DashboardTransferCountSerializer(serializers.ModelSerializer):
    transfer_count = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["transfer_count"]


class DashboardQueueRoomsSerializer(serializers.ModelSerializer):
    queue_rooms = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["queue_rooms"]


class DashboardActiveRoomsSerializer(serializers.ModelSerializer):
    active_rooms = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Room
        fields = ["active_rooms"]


class DashboardRoomSerializer(serializers.Serializer):
    waiting_time = serializers.IntegerField(allow_null=True, required=False)
    response_time = serializers.IntegerField(allow_null=True, required=False)
    interact_time = serializers.IntegerField(allow_null=True, required=False)
