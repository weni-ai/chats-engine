from rest_framework import serializers

from chats.apps.accounts.models import User


class BasicUserSerializer(serializers.Serializer):
    email = serializers.CharField(required=True, allow_blank=False)
    photo_url = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "photo_url",
        ]


class UserLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["language"]
        read_only = [
            "id",
            "email",
            "first_name",
            "last_name",
            "photo_url",
        ]
