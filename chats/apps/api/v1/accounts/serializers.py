from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer

from chats.apps.accounts.models import User


class LoginSerializer(AuthTokenSerializer, serializers.ModelSerializer):
    username = serializers.EmailField(label="Email")

    class Meta:
        model = User
        fields = ["username", "password"]
        ref_name = None
