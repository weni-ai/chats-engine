from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from chats.apps.api.v1.internal.permissions import ModuleHasPermission
from chats.apps.accounts.models import User
from chats.apps.api.v1.internal.users.serializers import (
    UserSerializer,
    UserLanguageSerializer,
)


class UserViewSet(ViewSet):
    def get_serializer(self, *args, **kwargs):
        return UserSerializer()

    def create(self, request):
        if not request.user.has_perm("accounts.can_communicate_internally"):
            raise ValidationError({"detail": "Not Allowed!"})

        serializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError({"detail": "invalid data!"})

        user = User.objects.get_or_create(email=serializer.data.get("email"))[0]

        if "photo_url" in serializer.data:
            user.photo_url = serializer.data.get("photo_url")

        if "first_name" in serializer.data:
            user.first_name = serializer.data.get("first_name")

        if "last_name" in serializer.data:
            user.last_name = serializer.data.get("last_name")

        user.save()

        serializer = UserSerializer(user)

        return Response(serializer.data)

    @action(detail=False, methods=["PUT", "PATCH"])
    def language(self, request, pk=None):
        user, created = User.objects.get_or_create(
            email=request.query_params.get("email"),
        )
        serializer = UserLanguageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.language = request.data["language"]
        user.save()
        return Response(UserLanguageSerializer(user).data)
