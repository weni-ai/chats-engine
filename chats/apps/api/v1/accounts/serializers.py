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
    full_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    last_interaction = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "status",
            "last_interaction",
        ]
        ref_name = None

    def get_full_name(self, user: User):
        return user.first_name + user.first_name

    def get_status(self, user: User):
        """
        TODO: Return if a user has active channel groups
        """
        return ""

    def get_last_interaction(self, user: User):
        return user.last_interaction
