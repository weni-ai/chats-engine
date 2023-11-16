from rest_framework import serializers

from chats.apps.accounts.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source="user.email")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")

    class Meta:
        model = Profile
        exclude = ["user", "uuid"]
