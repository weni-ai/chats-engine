from rest_framework import serializers

from chats.apps.api.v1.accounts.serializers import UserNameEmailSerializer

from ..models import DiscussionMessage, DiscussionMessageMedia


class DiscussionCreateMessageSerializer(serializers.Serializer):
    text = serializers.CharField(required=True)


"""
    {
        "content_type": "audio/wav",
        "created_on": "2022-12-15T18:06:45.654327-03:00",
        "message": "28e04b5a-9e70-4826-bd24-fed837661495",
        "url": "http://domain.com/recording.wav"
    }
"""


class MessageMediaSimpleSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DiscussionMessageMedia
        fields = [
            "content_type",
            "url",
            "created_on",
        ]

    def get_url(self, media: DiscussionMessageMedia):
        return media.url


class DiscussionReadMessageSerializer(serializers.ModelSerializer):
    user = UserNameEmailSerializer(many=False, required=False, read_only=True)
    media = MessageMediaSimpleSerializer(many=True, required=False)

    class Meta:
        model = DiscussionMessage
        fields = [
            "uuid",
            "user",
            "discussion",
            "text",
            "media",
            "created_on",
        ]


class MessageAndMediaSimpleSerializer(serializers.Serializer):
    text = serializers.CharField(required=False)
    content_type = serializers.CharField(required=True)
    media_file = serializers.FileField(required=True)
