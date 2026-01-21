from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chats.apps.accounts.models import Profile
from chats.apps.api.v1.users import serializers


class ProfileViewset(viewsets.GenericViewSet):
    swagger_tag = "Users"
    queryset = Profile.objects.all()
    serializer_class = serializers.ProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = None

    def get_object(self):
        return Profile.objects.get_or_create(user=self.request.user)[0]

    def update(self, request, **kwargs):
        user = request.user
        profile, created = Profile.objects.update_or_create(
            user=user, defaults=request.data
        )

        serializer = self.serializer_class(profile)

        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        project_uuid = request.query_params.get("project_uuid")
        serializer_context = {"project_uuid": project_uuid}

        obj = self.get_object()
        serializer = self.serializer_class(obj, context=serializer_context)
        return Response(serializer.data)
