from django.utils import timezone
from rest_framework import serializers

from chats.apps.csat.models import CSATSurvey
from chats.apps.rooms.models import Room


class BaseCSATWebhookSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    answered_on = serializers.DateTimeField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = CSATSurvey
        fields = ["room", "answered_on", "comment", "rating"]

    def validate(self, attrs):
        if not attrs.get("answered_on"):
            attrs["answered_on"] = timezone.now()

        return attrs


class CreateCSATWebhookSerializer(BaseCSATWebhookSerializer):
    rating = serializers.IntegerField(required=True, min_value=1, max_value=5)


class UpdateCSATWebhookSerializer(BaseCSATWebhookSerializer):
    rating = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=5
    )
