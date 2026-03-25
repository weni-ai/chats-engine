from rest_framework import serializers

from chats.apps.ai_features.audio_transcription.models import (
    AudioTranscription,
    AudioTranscriptionFeedback,
)


class AudioTranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioTranscription
        fields = ["uuid", "status", "text", "created_on"]
        read_only_fields = ["uuid", "status", "text", "created_on"]


class AudioTranscriptionCreateResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class AudioTranscriptionFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioTranscriptionFeedback
        fields = ["uuid", "liked", "text", "tags", "created_on"]
        read_only_fields = ["uuid", "created_on"]


class AudioTranscriptionFeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioTranscriptionFeedback
        fields = ["liked", "text", "tags"]


class MessageMediaTranscriptionSerializer(serializers.Serializer):
    """
    Serializer for the transcription field in the message media response.
    """

    text = serializers.CharField()
    feedback = serializers.SerializerMethodField()

    def get_feedback(self, obj):
        user = self.context.get("user")
        if not user:
            return None

        feedback = obj.feedbacks.filter(user=user).first()
        if feedback:
            return {"liked": feedback.liked}
        return None
