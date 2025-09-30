from django.utils import timezone
from rest_framework import serializers

from chats.apps.csat.models import CSATSurvey


class CSATWebhookSerializer(serializers.ModelSerializer):
    answered_on = serializers.DateTimeField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_null=True)
    rating = serializers.IntegerField(required=True, min_value=1, max_value=5)

    class Meta:
        model = CSATSurvey
        fields = ["room", "rating", "comment", "answered_on"]

    def validate(self, attrs):
        if not attrs.get("answered_on"):
            attrs["answered_on"] = timezone.now()

        return attrs
