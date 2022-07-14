from rest_framework import serializers

from chats.apps.quickmessages.models import QuickMessage


class QuickMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickMessage
        fields = "__all__"
        read_only_fields = ("user",)
