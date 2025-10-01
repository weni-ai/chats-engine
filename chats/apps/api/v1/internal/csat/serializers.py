from django.utils import timezone
from rest_framework import serializers

from chats.apps.rooms.models import Room


class CSATWebhookSerializer(serializers.Serializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    answered_on = serializers.DateTimeField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_null=True)
    rating = serializers.IntegerField(required=True, min_value=1, max_value=5)

    def validate(self, attrs):
        if not attrs.get("answered_on"):
            attrs["answered_on"] = timezone.now()

        return attrs
