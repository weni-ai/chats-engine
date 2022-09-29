from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from chats.apps.accounts.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        exclude = ["user", "uuid"]

    def get_email(self, profile: Profile):
        return profile.user.email
