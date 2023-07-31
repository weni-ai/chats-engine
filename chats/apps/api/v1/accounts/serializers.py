from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer

from chats.apps.accounts.models import User


class LoginSerializer(AuthTokenSerializer, serializers.ModelSerializer):
    username = serializers.EmailField(label="Email")

    class Meta:
        model = User
        fields = ["username", "password"]
        ref_name = None


class UserSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    last_interaction = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "status",
            "last_interaction",
        ]
        ref_name = None

    def get_status(self, user: User):
        """
        TODO: Return if a user has active channel groups
        """
        return ""

    def get_last_interaction(self, user: User):
        return user.last_interaction


class UserNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
        ]
