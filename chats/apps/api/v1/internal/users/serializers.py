from rest_framework import serializers

from chats.apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
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
